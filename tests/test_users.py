"""Tests for multi-user identity, per-user run ownership, and saved queries."""

from __future__ import annotations

import json

import exa_demo.api as api_module
import exa_demo.api_auth as auth_module
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
def client(tmp_path, monkeypatch):
    """TestClient with persistence pointed at temp dirs, no auth."""
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
    # Fresh rate limiter to avoid cross-test contamination.
    monkeypatch.setattr(
        auth_module, "rate_limiter", auth_module.RateLimiter()
    )
    return TestClient(api_module.app)


@pytest.fixture()
def multi_user_client(tmp_path, monkeypatch):
    """TestClient with multi-user auth enabled."""
    users = {"alice": "key-alice", "bob": "key-bob"}
    monkeypatch.setenv("PILOT_USERS", json.dumps(users))
    monkeypatch.setenv("PILOT_OPS_USERS", "alice")
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
    # Fresh rate limiter to avoid cross-test contamination.
    monkeypatch.setattr(
        auth_module, "rate_limiter", auth_module.RateLimiter()
    )
    return TestClient(api_module.app)


# ---------------------------------------------------------------------------
# Auth: multi-user key resolution
# ---------------------------------------------------------------------------


class TestMultiUserAuth:
    def test_multi_user_resolve_alice(self, multi_user_client):
        resp = multi_user_client.get(
            "/api/me",
            headers={"Authorization": "Bearer key-alice"},
        )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "alice"

    def test_multi_user_resolve_bob(self, multi_user_client):
        resp = multi_user_client.get(
            "/api/me",
            headers={"Authorization": "Bearer key-bob"},
        )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "bob"

    def test_multi_user_invalid_key(self, multi_user_client):
        resp = multi_user_client.get(
            "/api/me",
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert resp.status_code == 401

    def test_multi_user_no_header(self, multi_user_client):
        resp = multi_user_client.get("/api/me")
        assert resp.status_code == 401

    def test_default_user_when_no_auth(self, client):
        """Without PILOT_API_KEY or PILOT_USERS, user defaults to 'pilot'."""
        resp = client.get("/api/me")
        assert resp.status_code == 200
        assert resp.json()["user_id"] == "pilot"
        assert resp.json()["can_access_ops"] is True


# ---------------------------------------------------------------------------
# Per-user run ownership
# ---------------------------------------------------------------------------


class TestRunOwnership:
    def test_search_persists_user_id(self, multi_user_client):
        multi_user_client.post(
            "/api/search",
            json={"query": "test", "mode": "smoke"},
            headers={"Authorization": "Bearer key-alice"},
        )
        # Check via /api/me/runs.
        resp = multi_user_client.get(
            "/api/me/runs",
            headers={"Authorization": "Bearer key-alice"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert data["runs"][0]["user_id"] == "alice"

    def test_users_see_only_own_runs(self, multi_user_client):
        # Alice runs a search.
        multi_user_client.post(
            "/api/search",
            json={"query": "alice query", "mode": "smoke"},
            headers={"Authorization": "Bearer key-alice"},
        )
        # Bob runs a search.
        multi_user_client.post(
            "/api/search",
            json={"query": "bob query", "mode": "smoke"},
            headers={"Authorization": "Bearer key-bob"},
        )
        # Alice sees only her run.
        alice_runs = multi_user_client.get(
            "/api/me/runs",
            headers={"Authorization": "Bearer key-alice"},
        ).json()
        assert alice_runs["count"] == 1
        assert alice_runs["runs"][0]["query_preview"] == "alice query"

        # Bob sees only his run.
        bob_runs = multi_user_client.get(
            "/api/me/runs",
            headers={"Authorization": "Bearer key-bob"},
        ).json()
        assert bob_runs["count"] == 1
        assert bob_runs["runs"][0]["query_preview"] == "bob query"

    def test_allowlisted_ops_user_sees_all_runs(self, multi_user_client):
        """Allowlisted ops users retain access to the global /api/runs view."""
        multi_user_client.post(
            "/api/search",
            json={"query": "a", "mode": "smoke"},
            headers={"Authorization": "Bearer key-alice"},
        )
        multi_user_client.post(
            "/api/search",
            json={"query": "b", "mode": "smoke"},
            headers={"Authorization": "Bearer key-bob"},
        )
        all_runs = multi_user_client.get(
            "/api/runs",
            headers={"Authorization": "Bearer key-alice"},
        ).json()
        assert all_runs["count"] == 2

    def test_non_ops_user_cannot_access_global_runs(self, multi_user_client):
        multi_user_client.post(
            "/api/search",
            json={"query": "a", "mode": "smoke"},
            headers={"Authorization": "Bearer key-alice"},
        )
        resp = multi_user_client.get(
            "/api/runs",
            headers={"Authorization": "Bearer key-bob"},
        )
        assert resp.status_code == 403

    def test_non_ops_user_cannot_access_ops_summary(self, multi_user_client):
        resp = multi_user_client.get(
            "/api/ops/summary",
            headers={"Authorization": "Bearer key-bob"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# User summary (/api/me)
# ---------------------------------------------------------------------------


class TestUserSummary:
    def test_me_returns_usage(self, multi_user_client):
        multi_user_client.post(
            "/api/search",
            json={"query": "test", "mode": "smoke"},
            headers={"Authorization": "Bearer key-alice"},
        )
        resp = multi_user_client.get(
            "/api/me",
            headers={"Authorization": "Bearer key-alice"},
        )
        data = resp.json()
        assert data["user_id"] == "alice"
        assert data["usage"]["total_runs"] >= 1
        assert data["usage"]["completed"] >= 1
        assert data["can_access_ops"] is True

    def test_me_empty_for_new_user(self, multi_user_client):
        resp = multi_user_client.get(
            "/api/me",
            headers={"Authorization": "Bearer key-bob"},
        )
        data = resp.json()
        assert data["user_id"] == "bob"
        assert data["usage"]["total_runs"] == 0
        assert data["can_access_ops"] is False


# ---------------------------------------------------------------------------
# Saved queries CRUD
# ---------------------------------------------------------------------------


class TestSavedQueries:
    def test_create_and_list(self, multi_user_client):
        # Create a saved query.
        resp = multi_user_client.post(
            "/api/me/saved-queries",
            json={
                "workflow": "search",
                "query": "Florida CAT market",
                "label": "CAT market overview",
            },
            headers={"Authorization": "Bearer key-alice"},
        )
        assert resp.status_code == 201
        sq = resp.json()
        assert sq["workflow"] == "search"
        assert sq["query"] == "Florida CAT market"
        assert sq["label"] == "CAT market overview"
        assert sq["user_id"] == "alice"
        assert sq["id"]

        # List saved queries.
        list_resp = multi_user_client.get(
            "/api/me/saved-queries",
            headers={"Authorization": "Bearer key-alice"},
        )
        data = list_resp.json()
        assert data["count"] == 1
        assert data["queries"][0]["id"] == sq["id"]

    def test_delete_saved_query(self, multi_user_client):
        # Create.
        resp = multi_user_client.post(
            "/api/me/saved-queries",
            json={"workflow": "answer", "query": "test question"},
            headers={"Authorization": "Bearer key-alice"},
        )
        sq_id = resp.json()["id"]

        # Delete.
        del_resp = multi_user_client.delete(
            f"/api/me/saved-queries/{sq_id}",
            headers={"Authorization": "Bearer key-alice"},
        )
        assert del_resp.status_code == 204

        # Verify gone.
        list_resp = multi_user_client.get(
            "/api/me/saved-queries",
            headers={"Authorization": "Bearer key-alice"},
        )
        assert list_resp.json()["count"] == 0

    def test_delete_not_found(self, multi_user_client):
        resp = multi_user_client.delete(
            "/api/me/saved-queries/nonexistent",
            headers={"Authorization": "Bearer key-alice"},
        )
        assert resp.status_code == 404

    def test_users_cannot_see_other_saved_queries(self, multi_user_client):
        # Alice saves a query.
        multi_user_client.post(
            "/api/me/saved-queries",
            json={"workflow": "search", "query": "alice private"},
            headers={"Authorization": "Bearer key-alice"},
        )
        # Bob sees nothing.
        bob_resp = multi_user_client.get(
            "/api/me/saved-queries",
            headers={"Authorization": "Bearer key-bob"},
        )
        assert bob_resp.json()["count"] == 0

    def test_user_cannot_delete_others_query(self, multi_user_client):
        # Alice saves.
        resp = multi_user_client.post(
            "/api/me/saved-queries",
            json={"workflow": "search", "query": "alice only"},
            headers={"Authorization": "Bearer key-alice"},
        )
        sq_id = resp.json()["id"]

        # Bob tries to delete — should fail.
        del_resp = multi_user_client.delete(
            f"/api/me/saved-queries/{sq_id}",
            headers={"Authorization": "Bearer key-bob"},
        )
        assert del_resp.status_code == 404

        # Still exists for Alice.
        alice_resp = multi_user_client.get(
            "/api/me/saved-queries",
            headers={"Authorization": "Bearer key-alice"},
        )
        assert alice_resp.json()["count"] == 1

    def test_saved_query_count_in_me(self, multi_user_client):
        multi_user_client.post(
            "/api/me/saved-queries",
            json={"workflow": "search", "query": "q1"},
            headers={"Authorization": "Bearer key-alice"},
        )
        multi_user_client.post(
            "/api/me/saved-queries",
            json={"workflow": "answer", "query": "q2"},
            headers={"Authorization": "Bearer key-alice"},
        )
        me = multi_user_client.get(
            "/api/me",
            headers={"Authorization": "Bearer key-alice"},
        ).json()
        assert me["saved_query_count"] == 2


# ---------------------------------------------------------------------------
# Persistence unit tests
# ---------------------------------------------------------------------------


class TestSavedQueryPersistence:
    def test_save_and_list(self, repo):
        sq = persist_module.SavedQuery(
            user_id="alice",
            workflow="search",
            query="test query",
            label="test",
            created_at="2026-01-01T00:00:00Z",
        )
        repo.save_query(sq)
        queries = repo.list_saved_queries("alice")
        assert len(queries) == 1
        assert queries[0].id == sq.id
        assert queries[0].query == "test query"

    def test_delete(self, repo):
        sq = persist_module.SavedQuery(
            user_id="alice", workflow="search", query="q"
        )
        repo.save_query(sq)
        assert repo.delete_saved_query(sq.id, "alice") is True
        assert repo.list_saved_queries("alice") == []

    def test_delete_wrong_user(self, repo):
        sq = persist_module.SavedQuery(
            user_id="alice", workflow="search", query="q"
        )
        repo.save_query(sq)
        assert repo.delete_saved_query(sq.id, "bob") is False
        assert len(repo.list_saved_queries("alice")) == 1

    def test_user_summary(self, repo):
        repo.save(
            persist_module.RunRecord(
                workflow="search",
                mode="smoke",
                status="completed",
                user_id="alice",
                duration_ms=100.0,
            )
        )
        repo.save(
            persist_module.RunRecord(
                workflow="answer",
                mode="smoke",
                status="completed",
                user_id="bob",
            )
        )
        alice_summary = repo.user_summary("alice")
        assert alice_summary["total_runs"] == 1
        assert alice_summary["completed"] == 1

        bob_summary = repo.user_summary("bob")
        assert bob_summary["total_runs"] == 1

    def test_list_runs_user_filter(self, repo):
        repo.save(
            persist_module.RunRecord(
                workflow="search", mode="smoke", user_id="alice"
            )
        )
        repo.save(
            persist_module.RunRecord(
                workflow="search", mode="smoke", user_id="bob"
            )
        )
        alice_runs = repo.list_runs(user_id="alice")
        assert len(alice_runs) == 1
        assert alice_runs[0].user_id == "alice"

    def test_user_id_persisted_on_run(self, repo):
        rec = persist_module.RunRecord(
            workflow="search", mode="smoke", user_id="alice"
        )
        repo.save(rec)
        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.user_id == "alice"
