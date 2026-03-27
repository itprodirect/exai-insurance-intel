"""Tests for pilot auth, rate limiting, and boundary controls."""

from __future__ import annotations

import json

import exa_demo.api as api_module
import exa_demo.api_auth as auth_module
import pytest
from fastapi.testclient import TestClient


def _make_prepare_context_with_sqlite(sqlite_path):
    """Return a _prepare_context replacement that uses a temp sqlite path."""

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
def _base_patches(tmp_path, monkeypatch):
    """Shared patches: temp artifact dir, temp sqlite, fresh rate limiter."""
    monkeypatch.setattr(api_module, "ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setattr(
        api_module,
        "_prepare_context",
        _make_prepare_context_with_sqlite(tmp_path / "cache.sqlite"),
    )
    # Fresh rate limiter per test so state doesn't leak.
    monkeypatch.setattr(auth_module, "rate_limiter", auth_module.RateLimiter())


@pytest.fixture()
def open_client(_base_patches):
    """Client with auth disabled (no PILOT_API_KEY)."""
    return TestClient(api_module.app)


@pytest.fixture()
def auth_client(_base_patches, monkeypatch):
    """Client with auth enabled (PILOT_API_KEY=test-secret)."""
    monkeypatch.setenv("PILOT_API_KEY", "test-secret")
    return TestClient(api_module.app)


@pytest.fixture()
def multi_user_client(_base_patches, monkeypatch):
    """Client with per-user auth and a dedicated ops user."""
    monkeypatch.setenv(
        "PILOT_USERS",
        json.dumps(
            {
                "alice": "key-alice",
                "bob": "key-bob",
                "ops": "key-ops",
            }
        ),
    )
    monkeypatch.setenv("PILOT_OPS_USERS", "ops")
    return TestClient(api_module.app)


# ---------------------------------------------------------------------------
# Auth: bearer token
# ---------------------------------------------------------------------------


def test_health_no_auth_required(auth_client):
    """Health endpoint must remain open even when auth is enabled."""
    resp = auth_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_api_health_no_auth_required(auth_client):
    """The /api/health alias must also remain open."""
    resp = auth_client.get("/api/health")
    assert resp.status_code == 200


def test_auth_missing_header(auth_client):
    resp = auth_client.post("/api/search", json={"query": "test", "mode": "smoke"})
    assert resp.status_code == 401
    assert "Authorization" in resp.json()["detail"]


def test_auth_wrong_token(auth_client):
    resp = auth_client.post(
        "/api/search",
        json={"query": "test", "mode": "smoke"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert resp.status_code == 401


def test_auth_valid_token(auth_client):
    resp = auth_client.post(
        "/api/search",
        json={"query": "test", "mode": "smoke"},
        headers={"Authorization": "Bearer test-secret"},
    )
    assert resp.status_code == 200


def test_auth_disabled_when_no_key(open_client):
    """When PILOT_API_KEY is unset, requests pass without auth."""
    resp = open_client.post(
        "/api/search", json={"query": "test", "mode": "smoke"}
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


def test_rate_limit_enforced(auth_client, monkeypatch):
    """Requests beyond the limit get 429."""
    monkeypatch.setattr(
        auth_module, "rate_limiter", auth_module.RateLimiter(max_requests=2)
    )
    headers = {"Authorization": "Bearer test-secret"}
    for _ in range(2):
        resp = auth_client.post(
            "/api/search",
            json={"query": "test", "mode": "smoke"},
            headers=headers,
        )
        assert resp.status_code == 200

    resp = auth_client.post(
        "/api/search",
        json={"query": "test", "mode": "smoke"},
        headers=headers,
    )
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


# ---------------------------------------------------------------------------
# Mode validation
# ---------------------------------------------------------------------------


def test_invalid_mode_rejected(open_client):
    resp = open_client.post(
        "/api/search", json={"query": "test", "mode": "invalid"}
    )
    assert resp.status_code == 400
    assert "Invalid mode" in resp.json()["detail"]


def test_live_mode_blocked_by_default(open_client):
    resp = open_client.post(
        "/api/search", json={"query": "test", "mode": "live"}
    )
    assert resp.status_code == 403
    assert "Live mode" in resp.json()["detail"]


def test_live_mode_allowed_when_enabled(monkeypatch):
    """When PILOT_ALLOW_LIVE_MODE=1, validate_mode should not raise for 'live'."""
    monkeypatch.setenv("PILOT_ALLOW_LIVE_MODE", "1")
    # Call the validator directly — going through the full endpoint would
    # hit the real Exa API, which we don't want in unit tests.
    assert auth_module.validate_mode("live") == "live"


# ---------------------------------------------------------------------------
# Query boundary controls
# ---------------------------------------------------------------------------


def test_query_too_long_rejected(open_client, monkeypatch):
    monkeypatch.setenv("PILOT_MAX_QUERY_LENGTH", "10")
    resp = open_client.post(
        "/api/search", json={"query": "a" * 11, "mode": "smoke"}
    )
    assert resp.status_code == 400
    assert "Query too long" in resp.json()["detail"]


def test_num_results_clamped(open_client, monkeypatch):
    """Requesting more than PILOT_MAX_RESULTS should be silently clamped."""
    monkeypatch.setenv("PILOT_MAX_RESULTS", "3")
    resp = open_client.post(
        "/api/search",
        json={"query": "test", "mode": "smoke", "num_results": 50},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["record"]["result_count"] == 3


# ---------------------------------------------------------------------------
# Ops/admin allowlist
# ---------------------------------------------------------------------------


def test_ops_allowed_for_default_internal_user(open_client):
    runs = open_client.get("/api/runs")
    assert runs.status_code == 200

    summary = open_client.get("/api/ops/summary")
    assert summary.status_code == 200

    me = open_client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["can_access_ops"] is True


def test_ops_forbidden_for_non_allowlisted_user(_base_patches, monkeypatch):
    monkeypatch.setenv(
        "PILOT_USERS",
        json.dumps({"alice": "key-alice", "bob": "key-bob"}),
    )
    monkeypatch.setenv("PILOT_OPS_USERS", "alice")
    client = TestClient(api_module.app)

    runs = client.get(
        "/api/runs",
        headers={"Authorization": "Bearer key-bob"},
    )
    assert runs.status_code == 403

    summary = client.get(
        "/api/ops/summary",
        headers={"Authorization": "Bearer key-bob"},
    )
    assert summary.status_code == 403

    me = client.get(
        "/api/me",
        headers={"Authorization": "Bearer key-bob"},
    )
    assert me.status_code == 200
    assert me.json()["can_access_ops"] is False


# ---------------------------------------------------------------------------
# Single-record run/job authorization
# ---------------------------------------------------------------------------


def test_owner_can_read_own_research_job(multi_user_client):
    create = multi_user_client.post(
        "/api/research/jobs",
        json={"query": "Summarize the Florida CAT market outlook.", "mode": "smoke"},
        headers={"Authorization": "Bearer key-alice"},
    )
    assert create.status_code == 202
    job_id = create.json()["id"]

    resp = multi_user_client.get(
        f"/api/research/jobs/{job_id}",
        headers={"Authorization": "Bearer key-alice"},
    )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "alice"


def test_non_owner_cannot_read_another_users_research_job(multi_user_client):
    create = multi_user_client.post(
        "/api/research/jobs",
        json={"query": "Summarize the Florida CAT market outlook.", "mode": "smoke"},
        headers={"Authorization": "Bearer key-alice"},
    )
    assert create.status_code == 202
    job_id = create.json()["id"]

    resp = multi_user_client.get(
        f"/api/research/jobs/{job_id}",
        headers={"Authorization": "Bearer key-bob"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Job not found"


def test_ops_user_can_read_another_users_research_job(multi_user_client):
    create = multi_user_client.post(
        "/api/research/jobs",
        json={"query": "Summarize the Florida CAT market outlook.", "mode": "smoke"},
        headers={"Authorization": "Bearer key-alice"},
    )
    assert create.status_code == 202
    job_id = create.json()["id"]

    resp = multi_user_client.get(
        f"/api/research/jobs/{job_id}",
        headers={"Authorization": "Bearer key-ops"},
    )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "alice"


def test_owner_can_read_own_run_record(multi_user_client):
    create = multi_user_client.post(
        "/api/search",
        json={"query": "forensic engineer insurance", "mode": "smoke"},
        headers={"Authorization": "Bearer key-alice"},
    )
    assert create.status_code == 200

    runs = multi_user_client.get(
        "/api/me/runs",
        headers={"Authorization": "Bearer key-alice"},
    )
    assert runs.status_code == 200
    record_id = runs.json()["runs"][0]["id"]

    resp = multi_user_client.get(
        f"/api/runs/{record_id}",
        headers={"Authorization": "Bearer key-alice"},
    )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "alice"


def test_non_owner_cannot_read_another_users_run_record(multi_user_client):
    create = multi_user_client.post(
        "/api/search",
        json={"query": "forensic engineer insurance", "mode": "smoke"},
        headers={"Authorization": "Bearer key-alice"},
    )
    assert create.status_code == 200

    runs = multi_user_client.get(
        "/api/me/runs",
        headers={"Authorization": "Bearer key-alice"},
    )
    assert runs.status_code == 200
    record_id = runs.json()["runs"][0]["id"]

    resp = multi_user_client.get(
        f"/api/runs/{record_id}",
        headers={"Authorization": "Bearer key-bob"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Run not found"


def test_ops_user_can_read_another_users_run_record(multi_user_client):
    create = multi_user_client.post(
        "/api/search",
        json={"query": "forensic engineer insurance", "mode": "smoke"},
        headers={"Authorization": "Bearer key-alice"},
    )
    assert create.status_code == 200

    runs = multi_user_client.get(
        "/api/me/runs",
        headers={"Authorization": "Bearer key-alice"},
    )
    assert runs.status_code == 200
    record_id = runs.json()["runs"][0]["id"]

    resp = multi_user_client.get(
        f"/api/runs/{record_id}",
        headers={"Authorization": "Bearer key-ops"},
    )
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "alice"


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------


def test_request_id_header_present(open_client):
    resp = open_client.get("/health")
    assert "x-request-id" in resp.headers
    assert len(resp.headers["x-request-id"]) == 8
