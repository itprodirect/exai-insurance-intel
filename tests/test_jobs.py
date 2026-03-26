"""Tests for the async job system (jobs.py + API endpoints)."""

from __future__ import annotations

import time

import exa_demo.api as api_module
import exa_demo.jobs as jobs_module
import exa_demo.persistence as persist_module
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_prepare_context_with_sqlite(sqlite_path):
    def _prepare_context(mode, config_overrides=None):
        from exa_demo.cli_runtime import resolve_runtime, runtime_metadata
        from exa_demo.config import default_config, default_pricing

        config = default_config()
        config["sqlite_path"] = str(sqlite_path)
        pricing = default_pricing()
        if config_overrides:
            config.update(config_overrides)
        runtime = resolve_runtime(mode, run_id=None)
        meta = runtime_metadata(runtime)
        return config, pricing, runtime, meta

    return _prepare_context


@pytest.fixture()
def repo(tmp_path):
    return persist_module.LocalRunRepository(db_path=tmp_path / "runs.sqlite")


@pytest.fixture()
def store(tmp_path):
    return persist_module.LocalArtifactStore(base_dir=tmp_path / "store")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient with persistence pointed at temp dirs."""
    monkeypatch.setattr(api_module, "ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setattr(
        api_module,
        "_prepare_context",
        _make_prepare_context_with_sqlite(tmp_path / "cache.sqlite"),
    )
    monkeypatch.setattr(
        api_module,
        "run_repo",
        persist_module.LocalRunRepository(db_path=tmp_path / "runs.sqlite"),
    )
    monkeypatch.setattr(
        api_module,
        "artifact_store",
        persist_module.LocalArtifactStore(base_dir=tmp_path / "store"),
    )
    return TestClient(api_module.app)


# ---------------------------------------------------------------------------
# Unit tests: submit_job + _run_job
# ---------------------------------------------------------------------------


class TestSubmitJob:
    def test_returns_queued_record(self, repo, store):
        record = jobs_module.submit_job(
            run_repo=repo,
            artifact_store=store,
            workflow="research",
            mode="smoke",
            request_id="req-1",
            query_preview="test query",
            run_fn=lambda: {"run_id": "r1", "cache_hit": False, "summary": {}},
        )
        assert record.status == "queued"
        assert record.workflow == "research"
        assert record.mode == "smoke"
        assert record.request_id == "req-1"
        assert record.query_preview == "test query"

    def test_record_persisted_immediately(self, repo, store):
        record = jobs_module.submit_job(
            run_repo=repo,
            artifact_store=store,
            workflow="research",
            mode="smoke",
            request_id=None,
            query_preview="q",
            run_fn=lambda: {"run_id": "r1"},
        )
        restored = repo.get(record.id)
        assert restored is not None
        assert restored.status in ("queued", "running", "completed")

    def test_job_completes_successfully(self, repo, store):
        payload = {
            "run_id": "run-abc",
            "cache_hit": True,
            "summary": {"spent_usd": 0.01},
            "report": "Test report",
        }
        record = jobs_module.submit_job(
            run_repo=repo,
            artifact_store=store,
            workflow="research",
            mode="smoke",
            request_id=None,
            query_preview="test",
            run_fn=lambda: payload,
        )
        # Wait for background thread to finish.
        _wait_for_job(repo, record.id)

        completed = repo.get(record.id)
        assert completed is not None
        assert completed.status == "completed"
        assert completed.run_id == "run-abc"
        assert completed.cache_hit is True
        assert completed.duration_ms is not None
        assert completed.duration_ms >= 0
        assert completed.extra == {"result": payload}

    def test_job_failure_persists_error(self, repo, store):
        def failing_fn():
            raise ValueError("Something went wrong")

        record = jobs_module.submit_job(
            run_repo=repo,
            artifact_store=store,
            workflow="research",
            mode="smoke",
            request_id=None,
            query_preview="fail query",
            run_fn=failing_fn,
        )
        _wait_for_job(repo, record.id)

        failed = repo.get(record.id)
        assert failed is not None
        assert failed.status == "failed"
        assert "Something went wrong" in (failed.error_message or "")
        assert failed.duration_ms is not None

    def test_job_transitions_through_running(self, repo, store):
        """Verify the job passes through the running state."""
        observed_statuses = []

        original_save = repo.save

        def tracking_save(record):
            observed_statuses.append(record.status)
            return original_save(record)

        repo.save = tracking_save

        record = jobs_module.submit_job(
            run_repo=repo,
            artifact_store=store,
            workflow="research",
            mode="smoke",
            request_id=None,
            query_preview="test",
            run_fn=lambda: {"run_id": "r1"},
        )
        _wait_for_job(repo, record.id, use_tracking=False, original_get=repo.get)

        # queued (initial), running, completed
        assert "queued" in observed_statuses
        assert "running" in observed_statuses
        assert "completed" in observed_statuses


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestJobEndpoints:
    def test_submit_returns_202(self, client):
        resp = client.post(
            "/api/research/jobs",
            json={"query": "Florida CAT market", "mode": "smoke"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "queued"
        assert data["workflow"] == "research"
        assert data["id"]

    def test_poll_returns_completed(self, client):
        resp = client.post(
            "/api/research/jobs",
            json={"query": "test research query", "mode": "smoke"},
        )
        job_id = resp.json()["id"]

        # Wait for background execution.
        _wait_for_job(api_module.run_repo, job_id)

        poll = client.get(f"/api/research/jobs/{job_id}")
        assert poll.status_code == 200
        data = poll.json()
        assert data["status"] == "completed"
        assert data["result"] is not None
        assert data["duration_ms"] is not None

    def test_poll_not_found(self, client):
        resp = client.get("/api/research/jobs/nonexistent")
        assert resp.status_code == 404

    def test_poll_wrong_workflow_returns_404(self, client):
        """A run from a non-research workflow should not be returned."""
        # Create a search run directly in the repo.
        rec = persist_module.RunRecord(
            workflow="search", mode="smoke", status="completed"
        )
        api_module.run_repo.save(rec)

        resp = client.get(f"/api/research/jobs/{rec.id}")
        assert resp.status_code == 404

    def test_job_visible_in_runs_list(self, client):
        """Async jobs are runs — they should appear in /api/runs."""
        resp = client.post(
            "/api/research/jobs",
            json={"query": "visible in runs", "mode": "smoke"},
        )
        job_id = resp.json()["id"]
        _wait_for_job(api_module.run_repo, job_id)

        runs = client.get("/api/runs?workflow=research").json()
        job_ids = [r["id"] for r in runs["runs"]]
        assert job_id in job_ids

    def test_job_result_includes_report(self, client):
        resp = client.post(
            "/api/research/jobs",
            json={"query": "test query", "mode": "smoke"},
        )
        job_id = resp.json()["id"]
        _wait_for_job(api_module.run_repo, job_id)

        data = client.get(f"/api/research/jobs/{job_id}").json()
        assert data["status"] == "completed"
        result = data["result"]
        assert result is not None
        assert "run_id" in result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wait_for_job(
    repo,
    job_id: str,
    timeout: float = 10.0,
    interval: float = 0.05,
    *,
    use_tracking: bool = True,
    original_get=None,
):
    """Poll the repo until the job reaches a terminal state."""
    get_fn = original_get or repo.get
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rec = get_fn(job_id)
        if rec and rec.status in ("completed", "failed"):
            return
        time.sleep(interval)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")
