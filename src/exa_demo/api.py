"""Thin FastAPI wrapper over existing exa_demo workflows.

Run locally:
    uvicorn exa_demo.api:app --reload

All endpoints default to smoke mode (no network, no billing).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .cli_runtime import resolve_runtime, runtime_metadata
from .config import default_config, default_pricing
from .endpoint_workflows import (
    run_answer_workflow,
    run_find_similar_workflow,
    run_research_workflow,
    run_structured_search_workflow,
)
from .ranked_workflows import run_search_workflow

app = FastAPI(
    title="exai-insurance-intel API",
    description="Thin API wrapper over existing insurance intelligence workflows.",
    version="0.1.0",
)

# Configurable at module level; tests override these.
ARTIFACT_DIR = "experiments"


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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse, include_in_schema=False)
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse)
def api_search(req: SearchRequest) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {"num_results": req.num_results}
    if req.search_type is not None:
        overrides["search_type"] = req.search_type
    config, pricing, runtime, meta = _prepare_context(req.mode, overrides)
    payload, _record = run_search_workflow(
        query=req.query,
        artifact_dir=ARTIFACT_DIR,
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=meta,
    )
    return payload


@app.post("/api/answer", response_model=AnswerResponse)
def api_answer(req: AnswerRequest) -> Dict[str, Any]:
    config, pricing, runtime, meta = _prepare_context(req.mode)
    return run_answer_workflow(
        query=req.query,
        artifact_dir=ARTIFACT_DIR,
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=meta,
    )


@app.post("/api/research", response_model=ResearchResponse)
def api_research(req: ResearchRequest) -> Dict[str, Any]:
    config, pricing, runtime, meta = _prepare_context(req.mode)
    return run_research_workflow(
        query=req.query,
        artifact_dir=ARTIFACT_DIR,
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=meta,
    )


@app.post("/api/find-similar", response_model=FindSimilarResponse)
def api_find_similar(req: FindSimilarRequest) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {"num_results": req.num_results}
    config, pricing, runtime, meta = _prepare_context(req.mode, overrides)
    return run_find_similar_workflow(
        seed_url=req.url,
        artifact_dir=ARTIFACT_DIR,
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=meta,
    )


@app.post("/api/structured-search", response_model=StructuredSearchResponse)
def api_structured_search(req: StructuredSearchRequest) -> Dict[str, Any]:
    config, pricing, runtime, meta = _prepare_context(req.mode)
    # Workflow expects a file path; write inline schema to a temp file.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as fh:
        json.dump(req.output_schema, fh)
        schema_path = fh.name
    try:
        return run_structured_search_workflow(
            query=req.query,
            schema_file=schema_path,
            artifact_dir=ARTIFACT_DIR,
            config=config,
            pricing=pricing,
            runtime=runtime,
            runtime_metadata=meta,
        )
    finally:
        Path(schema_path).unlink(missing_ok=True)
