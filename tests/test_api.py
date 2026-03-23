"""Smoke-mode tests for the FastAPI wrapper endpoints."""

from __future__ import annotations

import exa_demo.api as api_module
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient wired to a temp artifact dir and sqlite path."""
    monkeypatch.setattr(api_module, "ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setattr(
        api_module,
        "_prepare_context",
        _make_prepare_context_with_sqlite(tmp_path / "cache.sqlite"),
    )
    return TestClient(api_module.app)


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


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


def test_search_smoke(client):
    resp = client.post(
        "/api/search",
        json={"query": "forensic engineer insurance", "mode": "smoke"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert "record" in data
    assert data["record"]["result_count"] == 5
    assert "taxonomy" in data
    assert "summary" in data
    assert "recommendation" in data


def test_search_custom_num_results(client):
    resp = client.post(
        "/api/search",
        json={
            "query": "public adjuster Florida",
            "mode": "smoke",
            "num_results": 3,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["record"]["result_count"] == 3


# ---------------------------------------------------------------------------
# Answer
# ---------------------------------------------------------------------------


def test_answer_smoke(client):
    resp = client.post(
        "/api/answer",
        json={
            "query": "What is the Florida appraisal clause dispute process?",
            "mode": "smoke",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["workflow"] == "answer"
    assert "run_id" in data
    assert "answer" in data
    assert "citations" in data
    assert isinstance(data["citation_count"], int)
    assert "summary" in data


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------


def test_research_smoke(client):
    resp = client.post(
        "/api/research",
        json={
            "query": "Summarize the Florida CAT market outlook.",
            "mode": "smoke",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["workflow"] == "research"
    assert "run_id" in data
    assert "report" in data
    assert "citations" in data
    assert isinstance(data["citation_count"], int)
    assert "summary" in data


# ---------------------------------------------------------------------------
# Find Similar
# ---------------------------------------------------------------------------


def test_find_similar_smoke(client):
    resp = client.post(
        "/api/find-similar",
        json={
            "url": "https://example.com/florida-appraisal-decision",
            "mode": "smoke",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["workflow"] == "find-similar"
    assert "run_id" in data
    assert "seed_url" in data
    assert isinstance(data["result_count"], int)
    assert "summary" in data


# ---------------------------------------------------------------------------
# Structured Search
# ---------------------------------------------------------------------------


def test_structured_search_smoke(client):
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "location": {"type": "string"},
        },
    }
    resp = client.post(
        "/api/structured-search",
        json={
            "query": "independent adjuster florida catastrophe",
            "output_schema": schema,
            "mode": "smoke",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["workflow"] == "structured-search"
    assert "run_id" in data
    assert "summary" in data


# ---------------------------------------------------------------------------
# Validation: bad requests
# ---------------------------------------------------------------------------


def test_search_missing_query(client):
    resp = client.post("/api/search", json={"mode": "smoke"})
    assert resp.status_code == 422


def test_search_invalid_num_results(client):
    resp = client.post(
        "/api/search",
        json={"query": "test", "mode": "smoke", "num_results": 0},
    )
    assert resp.status_code == 422
