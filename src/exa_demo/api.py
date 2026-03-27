"""Thin FastAPI wrapper over existing exa_demo workflows.

Run locally:
    uvicorn exa_demo.api:app --reload

All endpoints default to smoke mode (no network, no billing).

Auth / boundary controls are configured via environment variables.
See ``api_auth.py`` for details.

Persistence is configured via environment variables.
See ``persistence.py`` for details.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .api_auth import (
    RequestLoggingMiddleware,
    check_rate_limit,
    clamp_num_results,
    get_current_user,
    require_owner_or_ops_access,
    require_ops_access,
    require_api_key,
    user_can_access_ops,
    validate_mode,
    validate_query,
)
from .cli_runtime import resolve_runtime, runtime_metadata
from .config import default_config, default_pricing
from .endpoint_workflows import (
    run_answer_workflow,
    run_find_similar_workflow,
    run_research_workflow,
    run_structured_search_workflow,
)
from .jobs import submit_job
from .persistence import (
    SavedQuery,
    create_artifact_store,
    create_run_repository,
    persist_workflow_run,
    _utc_now,
)
from .ranked_workflows import run_search_workflow

logger = logging.getLogger("exa_demo.api")

app = FastAPI(
    title="exai-insurance-intel API",
    description="Thin API wrapper over existing insurance intelligence workflows.",
    version="0.1.0",
)

app.add_middleware(RequestLoggingMiddleware)

# Configurable at module level; tests override these.
ARTIFACT_DIR = "experiments"

# Module-level persistence backends; tests can replace via monkeypatch.
run_repo = create_run_repository()
artifact_store = create_artifact_store()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    query: str
    mode: str = Field(
        default="smoke",
        description="Execution mode: smoke, live, or auto",
    )
    search_type: Optional[str] = Field(
        default=None,
        description="Search type override (e.g. deep, deep-reasoning)",
    )
    num_results: int = Field(default=5, ge=1, le=100)


class AnswerRequest(BaseModel):
    query: str
    mode: str = Field(default="smoke")


class ResearchRequest(BaseModel):
    query: str
    mode: str = Field(default="smoke")


class FindSimilarRequest(BaseModel):
    url: str
    mode: str = Field(default="smoke")
    num_results: int = Field(default=5, ge=1, le=100)


class StructuredSearchRequest(BaseModel):
    query: str
    output_schema: Dict[str, Any] = Field(
        description="JSON Schema for structured extraction",
    )
    mode: str = Field(default="smoke")


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str


class SearchResponse(BaseModel):
    run_id: str
    artifact_dir: str
    record: Dict[str, Any]
    summary: Dict[str, Any]
    taxonomy: Dict[str, Any]
    recommendation: Dict[str, Any]


class AnswerResponse(BaseModel):
    workflow: str
    run_id: str
    artifact_dir: str
    answer: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = None
    citation_count: int = 0
    cache_hit: bool = False
    request_id: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)


class ResearchResponse(BaseModel):
    workflow: str
    run_id: str
    artifact_dir: str
    query: str
    report: Optional[str] = None
    report_preview: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = None
    citation_count: int = 0
    cache_hit: bool = False
    request_id: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)


class FindSimilarResponse(BaseModel):
    workflow: str
    run_id: str
    artifact_dir: str
    seed_url: str
    cache_hit: bool = False
    request_id: Optional[str] = None
    result_count: int = 0
    top_result: Optional[Dict[str, Any]] = None
    results: Optional[List[Dict[str, Any]]] = None
    summary: Dict[str, Any] = Field(default_factory=dict)


class StructuredSearchResponse(BaseModel):
    workflow: str
    run_id: str
    artifact_dir: str
    schema_file: str
    cache_hit: bool = False
    request_id: Optional[str] = None
    structured_output: Optional[Any] = None
    summary: Dict[str, Any] = Field(default_factory=dict)


class RunResponse(BaseModel):
    id: str
    request_id: Optional[str] = None
    run_id: Optional[str] = None
    workflow: str
    mode: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    query_preview: Optional[str] = None
    cache_hit: Optional[bool] = None
    cost_summary: Optional[Dict[str, Any]] = None
    artifact_location: Optional[str] = None
    artifact_count: int = 0
    error_message: Optional[str] = None
    user_id: Optional[str] = None


class JobResponse(RunResponse):
    result: Optional[Dict[str, Any]] = None


class RunListResponse(BaseModel):
    runs: List[RunResponse]
    count: int


class WorkflowBreakdown(BaseModel):
    workflow: str
    count: int
    avg_duration_ms: Optional[float] = None


class ModeBreakdown(BaseModel):
    mode: str
    count: int


class OpsSummaryResponse(BaseModel):
    total_runs: int = 0
    completed: int = 0
    failed: int = 0
    cache_hits: int = 0
    avg_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    total_spent_usd: float = 0.0
    earliest_run: Optional[str] = None
    latest_run: Optional[str] = None
    by_workflow: List[WorkflowBreakdown] = Field(default_factory=list)
    by_mode: List[ModeBreakdown] = Field(default_factory=list)


class SavedQueryRequest(BaseModel):
    workflow: str
    query: str
    label: Optional[str] = None


class SavedQueryResponse(BaseModel):
    id: str
    user_id: str
    workflow: str
    query: str
    label: Optional[str] = None
    created_at: Optional[str] = None


class SavedQueryListResponse(BaseModel):
    queries: List[SavedQueryResponse]
    count: int


class UserWorkflowBreakdown(BaseModel):
    workflow: str
    count: int


class UserSummary(BaseModel):
    total_runs: int = 0
    completed: int = 0
    failed: int = 0
    cache_hits: int = 0
    avg_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    earliest_run: Optional[str] = None
    latest_run: Optional[str] = None
    total_spent_usd: float = 0.0
    by_workflow: List[UserWorkflowBreakdown] = Field(default_factory=list)


class MeResponse(BaseModel):
    user_id: str
    usage: UserSummary
    saved_query_count: int
    can_access_ops: bool


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _prepare_context(
    mode: str,
    config_overrides: Dict[str, Any] | None = None,
) -> tuple[Dict[str, Any], Dict[str, float], Any, Dict[str, Any]]:
    """Build (config, pricing, runtime, runtime_metadata) for a workflow call."""
    config = default_config()
    pricing = default_pricing()
    if config_overrides:
        config.update(config_overrides)
    runtime = resolve_runtime(mode, run_id=None)
    meta = runtime_metadata(runtime)
    return config, pricing, runtime, meta


def _get_request_id(request: Request) -> Optional[str]:
    """Extract request_id set by RequestLoggingMiddleware, if available."""
    return getattr(request.state, "request_id", None)


def _persist(
    *,
    workflow: str,
    mode: str,
    request_id: Optional[str],
    payload: Dict[str, Any],
    query_preview: Optional[str] = None,
    started_at: Optional[str] = None,
    duration_ms: Optional[float] = None,
    status: str = "completed",
    error_message: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """Best-effort persistence — never fails the request."""
    try:
        persist_workflow_run(
            run_repo=run_repo,
            artifact_store=artifact_store,
            workflow=workflow,
            mode=mode,
            request_id=request_id,
            payload=payload,
            query_preview=query_preview,
            artifact_dir=ARTIFACT_DIR,
            started_at=started_at,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            user_id=user_id,
        )
    except Exception:
        logger.exception("Failed to persist run metadata")


# ---------------------------------------------------------------------------
# Health endpoints (no auth required)
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse, include_in_schema=False)
def health() -> Dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Authenticated API router
# ---------------------------------------------------------------------------

api_router = APIRouter(
    prefix="/api",
    dependencies=[Depends(require_api_key), Depends(check_rate_limit)],
)


@api_router.post("/search", response_model=SearchResponse)
def api_search(req: SearchRequest, request: Request) -> Dict[str, Any]:
    validate_mode(req.mode)
    validate_query(req.query)
    clamped = clamp_num_results(req.num_results)
    overrides: Dict[str, Any] = {"num_results": clamped}
    if req.search_type is not None:
        overrides["search_type"] = req.search_type
    config, pricing, runtime, meta = _prepare_context(req.mode, overrides)
    rid = _get_request_id(request)
    uid = get_current_user(request)
    started_at = _utc_now()
    t0 = time.monotonic()
    try:
        payload, _record = run_search_workflow(
            query=req.query,
            artifact_dir=ARTIFACT_DIR,
            config=config,
            pricing=pricing,
            runtime=runtime,
            runtime_metadata=meta,
        )
        duration_ms = (time.monotonic() - t0) * 1000
        _persist(
            workflow="search",
            mode=req.mode,
            request_id=rid,
            payload=payload,
            query_preview=req.query,
            started_at=started_at,
            duration_ms=duration_ms,
            user_id=uid,
        )
        return payload
    except Exception as exc:
        duration_ms = (time.monotonic() - t0) * 1000
        _persist(
            workflow="search",
            mode=req.mode,
            request_id=rid,
            payload={},
            query_preview=req.query,
            started_at=started_at,
            duration_ms=duration_ms,
            status="failed",
            error_message=str(exc)[:500],
            user_id=uid,
        )
        raise


@api_router.post("/answer", response_model=AnswerResponse)
def api_answer(req: AnswerRequest, request: Request) -> Dict[str, Any]:
    validate_mode(req.mode)
    validate_query(req.query)
    config, pricing, runtime, meta = _prepare_context(req.mode)
    rid = _get_request_id(request)
    uid = get_current_user(request)
    started_at = _utc_now()
    t0 = time.monotonic()
    try:
        payload = run_answer_workflow(
            query=req.query,
            artifact_dir=ARTIFACT_DIR,
            config=config,
            pricing=pricing,
            runtime=runtime,
            runtime_metadata=meta,
        )
        duration_ms = (time.monotonic() - t0) * 1000
        _persist(
            workflow="answer",
            mode=req.mode,
            request_id=rid,
            payload=payload,
            query_preview=req.query,
            started_at=started_at,
            duration_ms=duration_ms,
            user_id=uid,
        )
        return payload
    except Exception as exc:
        duration_ms = (time.monotonic() - t0) * 1000
        _persist(
            workflow="answer",
            mode=req.mode,
            request_id=rid,
            payload={},
            query_preview=req.query,
            started_at=started_at,
            duration_ms=duration_ms,
            status="failed",
            error_message=str(exc)[:500],
            user_id=uid,
        )
        raise


@api_router.post("/research", response_model=ResearchResponse)
def api_research(req: ResearchRequest, request: Request) -> Dict[str, Any]:
    validate_mode(req.mode)
    validate_query(req.query)
    config, pricing, runtime, meta = _prepare_context(req.mode)
    rid = _get_request_id(request)
    uid = get_current_user(request)
    started_at = _utc_now()
    t0 = time.monotonic()
    try:
        payload = run_research_workflow(
            query=req.query,
            artifact_dir=ARTIFACT_DIR,
            config=config,
            pricing=pricing,
            runtime=runtime,
            runtime_metadata=meta,
        )
        duration_ms = (time.monotonic() - t0) * 1000
        _persist(
            workflow="research",
            mode=req.mode,
            request_id=rid,
            payload=payload,
            query_preview=req.query,
            started_at=started_at,
            duration_ms=duration_ms,
            user_id=uid,
        )
        return payload
    except Exception as exc:
        duration_ms = (time.monotonic() - t0) * 1000
        _persist(
            workflow="research",
            mode=req.mode,
            request_id=rid,
            payload={},
            query_preview=req.query,
            started_at=started_at,
            duration_ms=duration_ms,
            status="failed",
            error_message=str(exc)[:500],
            user_id=uid,
        )
        raise


@api_router.post(
    "/research/jobs",
    response_model=JobResponse,
    status_code=202,
)
def api_submit_research_job(
    req: ResearchRequest, request: Request
) -> Dict[str, Any]:
    validate_mode(req.mode)
    validate_query(req.query)
    config, pricing, runtime, meta = _prepare_context(req.mode)
    rid = _get_request_id(request)
    uid = get_current_user(request)

    record = submit_job(
        run_repo=run_repo,
        artifact_store=artifact_store,
        workflow="research",
        mode=req.mode,
        request_id=rid,
        query_preview=req.query,
        run_fn=lambda: run_research_workflow(
            query=req.query,
            artifact_dir=ARTIFACT_DIR,
            config=config,
            pricing=pricing,
            runtime=runtime,
            runtime_metadata=meta,
        ),
        artifact_dir=ARTIFACT_DIR,
        user_id=uid,
    )
    return _job_to_dict(record)


@api_router.get("/research/jobs/{job_id}", response_model=JobResponse)
def api_get_research_job(job_id: str, request: Request) -> Dict[str, Any]:
    record = run_repo.get(job_id)
    if record is None or record.workflow != "research":
        raise HTTPException(status_code=404, detail="Job not found")
    require_owner_or_ops_access(
        request,
        record.user_id,
        not_found_detail="Job not found",
    )
    return _job_to_dict(record)


@api_router.post("/find-similar", response_model=FindSimilarResponse)
def api_find_similar(req: FindSimilarRequest, request: Request) -> Dict[str, Any]:
    validate_mode(req.mode)
    clamped = clamp_num_results(req.num_results)
    overrides: Dict[str, Any] = {"num_results": clamped}
    config, pricing, runtime, meta = _prepare_context(req.mode, overrides)
    rid = _get_request_id(request)
    uid = get_current_user(request)
    started_at = _utc_now()
    t0 = time.monotonic()
    try:
        payload = run_find_similar_workflow(
            seed_url=req.url,
            artifact_dir=ARTIFACT_DIR,
            config=config,
            pricing=pricing,
            runtime=runtime,
            runtime_metadata=meta,
        )
        duration_ms = (time.monotonic() - t0) * 1000
        _persist(
            workflow="find-similar",
            mode=req.mode,
            request_id=rid,
            payload=payload,
            query_preview=req.url,
            started_at=started_at,
            duration_ms=duration_ms,
            user_id=uid,
        )
        return payload
    except Exception as exc:
        duration_ms = (time.monotonic() - t0) * 1000
        _persist(
            workflow="find-similar",
            mode=req.mode,
            request_id=rid,
            payload={},
            query_preview=req.url,
            started_at=started_at,
            duration_ms=duration_ms,
            status="failed",
            error_message=str(exc)[:500],
            user_id=uid,
        )
        raise


@api_router.post("/structured-search", response_model=StructuredSearchResponse)
def api_structured_search(
    req: StructuredSearchRequest, request: Request
) -> Dict[str, Any]:
    validate_mode(req.mode)
    validate_query(req.query)
    config, pricing, runtime, meta = _prepare_context(req.mode)
    rid = _get_request_id(request)
    uid = get_current_user(request)
    started_at = _utc_now()
    t0 = time.monotonic()
    # Workflow expects a file path; write inline schema to a temp file.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as fh:
        json.dump(req.output_schema, fh)
        schema_path = fh.name
    try:
        payload = run_structured_search_workflow(
            query=req.query,
            schema_file=schema_path,
            artifact_dir=ARTIFACT_DIR,
            config=config,
            pricing=pricing,
            runtime=runtime,
            runtime_metadata=meta,
        )
        duration_ms = (time.monotonic() - t0) * 1000
        _persist(
            workflow="structured-search",
            mode=req.mode,
            request_id=rid,
            payload=payload,
            query_preview=req.query,
            started_at=started_at,
            duration_ms=duration_ms,
            user_id=uid,
        )
        return payload
    except Exception as exc:
        duration_ms = (time.monotonic() - t0) * 1000
        _persist(
            workflow="structured-search",
            mode=req.mode,
            request_id=rid,
            payload={},
            query_preview=req.query,
            started_at=started_at,
            duration_ms=duration_ms,
            status="failed",
            error_message=str(exc)[:500],
            user_id=uid,
        )
        raise
    finally:
        Path(schema_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# User endpoints (/api/me/*)
# ---------------------------------------------------------------------------


@api_router.get("/me", response_model=MeResponse)
def api_me(request: Request) -> Dict[str, Any]:
    """Return the current user's profile and usage summary."""
    uid = get_current_user(request)
    usage = run_repo.user_summary(uid)
    saved_count = len(run_repo.list_saved_queries(uid))
    return {
        "user_id": uid,
        "usage": usage,
        "saved_query_count": saved_count,
        "can_access_ops": user_can_access_ops(uid),
    }


@api_router.get("/me/runs", response_model=RunListResponse)
def api_my_runs(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    workflow: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    """List runs belonging to the current user."""
    uid = get_current_user(request)
    capped_limit = min(limit, 200)
    runs = run_repo.list_runs(
        limit=capped_limit,
        offset=offset,
        workflow=workflow,
        status=status,
        user_id=uid,
    )
    return {
        "runs": [_run_to_dict(r) for r in runs],
        "count": len(runs),
    }


@api_router.get("/me/saved-queries", response_model=SavedQueryListResponse)
def api_list_saved_queries(request: Request) -> Dict[str, Any]:
    uid = get_current_user(request)
    queries = run_repo.list_saved_queries(uid)
    return {
        "queries": [
            {
                "id": sq.id,
                "user_id": sq.user_id,
                "workflow": sq.workflow,
                "query": sq.query,
                "label": sq.label,
                "created_at": sq.created_at,
            }
            for sq in queries
        ],
        "count": len(queries),
    }


@api_router.post(
    "/me/saved-queries",
    response_model=SavedQueryResponse,
    status_code=201,
)
def api_save_query(
    req: SavedQueryRequest, request: Request
) -> Dict[str, Any]:
    uid = get_current_user(request)
    sq = SavedQuery(
        user_id=uid,
        workflow=req.workflow,
        query=req.query,
        label=req.label,
        created_at=_utc_now(),
    )
    run_repo.save_query(sq)
    return {
        "id": sq.id,
        "user_id": sq.user_id,
        "workflow": sq.workflow,
        "query": sq.query,
        "label": sq.label,
        "created_at": sq.created_at,
    }


@api_router.delete("/me/saved-queries/{query_id}", status_code=204)
def api_delete_saved_query(query_id: str, request: Request) -> None:
    uid = get_current_user(request)
    deleted = run_repo.delete_saved_query(query_id, uid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved query not found")


# ---------------------------------------------------------------------------
# Run history + ops endpoints
# ---------------------------------------------------------------------------


@api_router.get("/runs", response_model=RunListResponse)
def api_list_runs(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    workflow: Optional[str] = None,
    mode: Optional[str] = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    require_ops_access(request)
    capped_limit = min(limit, 200)
    runs = run_repo.list_runs(
        limit=capped_limit,
        offset=offset,
        workflow=workflow,
        mode=mode,
        status=status,
    )
    return {
        "runs": [_run_to_dict(r) for r in runs],
        "count": len(runs),
    }


@api_router.get("/runs/{record_id}", response_model=RunResponse)
def api_get_run(record_id: str, request: Request) -> Dict[str, Any]:
    record = run_repo.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    require_owner_or_ops_access(
        request,
        record.user_id,
        not_found_detail="Run not found",
    )
    return _run_to_dict(record)


@api_router.get("/ops/summary", response_model=OpsSummaryResponse)
def api_ops_summary(request: Request) -> Dict[str, Any]:
    require_ops_access(request)
    return run_repo.summary()


def _run_to_dict(record) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
    """Convert a RunRecord to a response-safe dict."""
    return asdict(record)


def _job_to_dict(record) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
    """Convert a RunRecord job into the API response shape."""
    payload = _run_to_dict(record)
    result = None
    if isinstance(record.extra, dict):
        result = record.extra.get("result")
    payload["result"] = result
    return payload


app.include_router(api_router)
