"""Tests for the pilot persistence layer."""

from __future__ import annotations

import json
from pathlib import Path

import exa_demo.api as api_module
import exa_demo.persistence as persist_module
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# RunRecord unit tests
# ---------------------------------------------------------------------------


class TestRunRecord:
    def test_defaults(self):
        rec = persist_module.RunRecord(workflow="search", mode="smoke")
        assert rec.status == "pending"
        assert rec.id  # auto-generated
        assert len(rec.id) == 12

    def test_to_dict_serializes_nested(self):
        rec = persist_module.RunRecord(
            workflow="answer",
            mode="smoke",
            cost_summary={"spent_usd": 0.01},
        )
        d = rec.to_dict()
        assert isinstance(d["cost_summary"], str)
        assert json.loads(d["cost_summary"]) == {"spent_usd": 0.01}

    def test_from_row_round_trip(self):
        rec = persist_module.RunRecord(
            workflow="research",
            mode="live",
            cost_summary={"spent_usd": 0.5},
            extra={"note": "test"},
        )
        d = rec.to_dict()
        restored = persist_module.RunRecord.from_row(d)
        assert restored.workflow == "research"
        assert restored.cost_summary == {"spent_usd": 0.5}
        assert restored.extra == {"note": "test"}


# ---------------------------------------------------------------------------
# Query preview helper
# ---------------------------------------------------------------------------


class TestQueryPreview:
    def test_short_query(self):
        assert persist_module._query_preview("hello") == "hello"

    def test_long_query_truncated(self):
        long = "x" * 300
        preview = persist_module._query_preview(long)
        assert len(preview) == 203  # 200 + "..."
        assert preview.endswith("...")

    def test_none_returns_none(self):
        assert persist_module._query_preview(None) is None


# ---------------------------------------------------------------------------
# LocalArtifactStore
# ---------------------------------------------------------------------------


class TestLocalArtifactStore:
    def test_upload_and_list(self, tmp_path):
        store = persist_module.LocalArtifactStore(base_dir=tmp_path / "store")
        source = tmp_path / "source.json"
        source.write_text('{"a": 1}')
        loc = store.upload("run-1", "source.json", source)
        assert Path(loc).exists()
        artifacts = store.list_artifacts("run-1")
        assert len(artifacts) == 1

    def test_upload_directory(self, tmp_path):
        store = persist_module.LocalArtifactStore(base_dir=tmp_path / "store")
        src_dir = tmp_path / "artifacts" / "run-2"
        src_dir.mkdir(parents=True)
        (src_dir / "a.json").write_text("{}")
        (src_dir / "b.json").write_text("{}")
        locs = store.upload_directory("run-2", src_dir)
        assert len(locs) == 2

    def test_upload_missing_file_raises(self, tmp_path):
        store = persist_module.LocalArtifactStore(base_dir=tmp_path / "store")
        with pytest.raises(FileNotFoundError):
            store.upload("run-x", "missing.json", tmp_path / "no.json")

    def test_list_empty_run(self, tmp_path):
        store = persist_module.LocalArtifactStore(base_dir=tmp_path / "store")
        assert store.list_artifacts("nonexistent") == []


# ---------------------------------------------------------------------------
# LocalRunRepository
# ---------------------------------------------------------------------------


class TestLocalRunRepository:
    def test_save_and_get(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        rec = persist_module.RunRecord(
            workflow="search",
            mode="smoke",
            status="completed",
            query_preview="test query",
            cache_hit=True,
            cost_summary={"spent_usd": 0.0},
        )
        repo.save(rec)
        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.workflow == "search"
        assert restored.cache_hit is True
        assert restored.cost_summary == {"spent_usd": 0.0}

    def test_upsert(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        rec = persist_module.RunRecord(
            workflow="answer", mode="smoke", status="pending"
        )
        repo.save(rec)
        rec.status = "completed"
        repo.save(rec)
        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.status == "completed"

    def test_list_runs_ordering(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        for i in range(5):
            rec = persist_module.RunRecord(
                workflow="search",
                mode="smoke",
                started_at=f"2026-03-22T00:0{i}:00Z",
            )
            repo.save(rec)
        runs = repo.list_runs(limit=3)
        assert len(runs) == 3
        # Most recent first.
        assert runs[0].started_at > runs[1].started_at  # type: ignore[operator]

    def test_get_missing_returns_none(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        assert repo.get("nonexistent") is None

    def test_cache_hit_false(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        rec = persist_module.RunRecord(
            workflow="search", mode="smoke", cache_hit=False
        )
        repo.save(rec)
        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.cache_hit is False

    def test_cache_hit_none(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        rec = persist_module.RunRecord(workflow="search", mode="smoke")
        repo.save(rec)
        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.cache_hit is None


# ---------------------------------------------------------------------------
# persist_workflow_run integration
# ---------------------------------------------------------------------------


class TestPersistWorkflowRun:
    def test_persist_creates_record(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        store = persist_module.LocalArtifactStore(
            base_dir=tmp_path / "store"
        )
        payload = {
            "run_id": "test-run-123",
            "summary": {"spent_usd": 0.0, "cache_hits": 1},
            "cache_hit": True,
        }
        record = persist_module.persist_workflow_run(
            run_repo=repo,
            artifact_store=store,
            workflow="answer",
            mode="smoke",
            request_id="abc123",
            payload=payload,
            query_preview="What is Florida appraisal?",
        )
        assert record.workflow == "answer"
        assert record.cache_hit is True
        assert record.run_id == "test-run-123"

        restored = repo.get(record.id)
        assert restored is not None
        assert restored.request_id == "abc123"

    def test_persist_uploads_artifacts(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        store = persist_module.LocalArtifactStore(
            base_dir=tmp_path / "store"
        )
        # Create a fake artifact directory.
        art_dir = tmp_path / "experiments" / "run-42"
        art_dir.mkdir(parents=True)
        (art_dir / "config.json").write_text("{}")
        (art_dir / "summary.json").write_text("{}")

        payload = {"run_id": "run-42", "summary": {}}
        record = persist_module.persist_workflow_run(
            run_repo=repo,
            artifact_store=store,
            workflow="search",
            mode="smoke",
            request_id=None,
            payload=payload,
            artifact_dir=str(tmp_path / "experiments"),
        )
        assert record.artifact_count == 2


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


class TestFactories:
    def test_create_artifact_store_local(self, monkeypatch):
        monkeypatch.delenv("PILOT_ARTIFACT_STORE", raising=False)
        store = persist_module.create_artifact_store()
        assert isinstance(store, persist_module.LocalArtifactStore)

    def test_create_artifact_store_s3_requires_bucket(self, monkeypatch):
        monkeypatch.setenv("PILOT_ARTIFACT_STORE", "s3")
        monkeypatch.delenv("PILOT_S3_BUCKET", raising=False)
        with pytest.raises(RuntimeError, match="PILOT_S3_BUCKET"):
            persist_module.create_artifact_store()

    def test_create_run_repository_local(self, monkeypatch):
        monkeypatch.delenv("PILOT_RUN_STORE", raising=False)
        repo = persist_module.create_run_repository()
        assert isinstance(repo, persist_module.LocalRunRepository)

    def test_create_run_repository_postgres_requires_url(self, monkeypatch):
        monkeypatch.setenv("PILOT_RUN_STORE", "postgres")
        monkeypatch.delenv("PILOT_POSTGRES_URL", raising=False)
        with pytest.raises(RuntimeError, match="PILOT_POSTGRES_URL"):
            persist_module.create_run_repository()


# ---------------------------------------------------------------------------
# API integration: /api/runs endpoints
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


def test_search_persists_run(client):
    resp = client.post(
        "/api/search", json={"query": "test query", "mode": "smoke"}
    )
    assert resp.status_code == 200

    runs_resp = client.get("/api/runs")
    assert runs_resp.status_code == 200
    data = runs_resp.json()
    assert data["count"] >= 1
    run = data["runs"][0]
    assert run["workflow"] == "search"
    assert run["mode"] == "smoke"
    assert run["status"] == "completed"
    assert run["query_preview"] == "test query"


def test_get_run_by_id(client):
    client.post("/api/search", json={"query": "test", "mode": "smoke"})
    runs = client.get("/api/runs").json()["runs"]
    record_id = runs[0]["id"]

    resp = client.get(f"/api/runs/{record_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == record_id


def test_get_run_not_found(client):
    resp = client.get("/api/runs/nonexistent")
    assert resp.status_code == 404


def test_runs_list_pagination(client):
    for i in range(3):
        client.post(
            "/api/search", json={"query": f"query {i}", "mode": "smoke"}
        )
    resp = client.get("/api/runs?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2

    resp2 = client.get("/api/runs?limit=2&offset=2")
    data2 = resp2.json()
    assert data2["count"] == 1


def test_answer_persists_run(client):
    client.post(
        "/api/answer",
        json={"query": "What is appraisal?", "mode": "smoke"},
    )
    runs = client.get("/api/runs").json()["runs"]
    answer_runs = [r for r in runs if r["workflow"] == "answer"]
    assert len(answer_runs) == 1
    assert answer_runs[0]["query_preview"] == "What is appraisal?"


# ---------------------------------------------------------------------------
# Duration and timing
# ---------------------------------------------------------------------------


class TestDuration:
    def test_duration_persisted(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        rec = persist_module.RunRecord(
            workflow="search", mode="smoke", duration_ms=123.4
        )
        repo.save(rec)
        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.duration_ms == 123.4

    def test_persist_workflow_run_with_duration(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        store = persist_module.LocalArtifactStore(
            base_dir=tmp_path / "store"
        )
        record = persist_module.persist_workflow_run(
            run_repo=repo,
            artifact_store=store,
            workflow="search",
            mode="smoke",
            request_id=None,
            payload={"run_id": "x", "summary": {}},
            duration_ms=456.78,
        )
        assert record.duration_ms == 456.8  # rounded


class TestErrorMessage:
    def test_error_message_persisted(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        rec = persist_module.RunRecord(
            workflow="search",
            mode="smoke",
            status="failed",
            error_message="Something broke",
        )
        repo.save(rec)
        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.error_message == "Something broke"


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


class TestFiltering:
    def test_filter_by_workflow(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        for wf in ("search", "search", "answer"):
            repo.save(persist_module.RunRecord(workflow=wf, mode="smoke"))
        assert len(repo.list_runs(workflow="search")) == 2
        assert len(repo.list_runs(workflow="answer")) == 1

    def test_filter_by_status(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        repo.save(
            persist_module.RunRecord(
                workflow="search", mode="smoke", status="completed"
            )
        )
        repo.save(
            persist_module.RunRecord(
                workflow="search", mode="smoke", status="failed"
            )
        )
        assert len(repo.list_runs(status="completed")) == 1
        assert len(repo.list_runs(status="failed")) == 1

    def test_filter_by_mode(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        repo.save(
            persist_module.RunRecord(workflow="search", mode="smoke")
        )
        repo.save(
            persist_module.RunRecord(workflow="search", mode="live")
        )
        assert len(repo.list_runs(mode="smoke")) == 1


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class TestSummary:
    def test_summary_empty(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        s = repo.summary()
        assert s["total_runs"] == 0
        assert s["total_spent_usd"] == 0.0

    def test_summary_with_data(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        repo.save(
            persist_module.RunRecord(
                workflow="search",
                mode="smoke",
                status="completed",
                duration_ms=100.0,
                cache_hit=True,
                cost_summary={"spent_usd": 0.005},
            )
        )
        repo.save(
            persist_module.RunRecord(
                workflow="answer",
                mode="smoke",
                status="completed",
                duration_ms=200.0,
                cache_hit=False,
                cost_summary={"spent_usd": 0.01},
            )
        )
        repo.save(
            persist_module.RunRecord(
                workflow="search",
                mode="smoke",
                status="failed",
                duration_ms=50.0,
                error_message="test error",
            )
        )
        s = repo.summary()
        assert s["total_runs"] == 3
        assert s["completed"] == 2
        assert s["failed"] == 1
        assert s["cache_hits"] == 1
        assert s["avg_duration_ms"] is not None
        assert s["total_spent_usd"] == 0.015
        assert len(s["by_workflow"]) == 2
        assert len(s["by_mode"]) == 1


# ---------------------------------------------------------------------------
# API: ops/summary endpoint
# ---------------------------------------------------------------------------


def test_ops_summary_endpoint(client):
    client.post("/api/search", json={"query": "test", "mode": "smoke"})
    resp = client.get("/api/ops/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_runs"] >= 1
    assert data["completed"] >= 1
    assert "by_workflow" in data
    assert "by_mode" in data


def test_search_run_has_duration(client):
    client.post("/api/search", json={"query": "test", "mode": "smoke"})
    runs = client.get("/api/runs").json()["runs"]
    assert runs[0]["duration_ms"] is not None
    assert runs[0]["duration_ms"] > 0


def test_runs_filter_by_workflow(client):
    client.post("/api/search", json={"query": "test", "mode": "smoke"})
    client.post(
        "/api/answer", json={"query": "test question", "mode": "smoke"}
    )
    resp = client.get("/api/runs?workflow=answer")
    data = resp.json()
    assert data["count"] == 1
    assert data["runs"][0]["workflow"] == "answer"
