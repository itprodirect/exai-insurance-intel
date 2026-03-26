"""In-process async job runner for long-running pilot workflows.

Uses a ThreadPoolExecutor so jobs run in background threads without
blocking the HTTP request. Job state is persisted in the existing
RunRepository so it survives UI refreshes and is visible in ops.

This module is intentionally simple and replaceable — a future slice
can swap in Redis/Celery/SQS without changing the API contract.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

from .persistence import (
    ArtifactStore,
    RunRecord,
    RunRepository,
    _query_preview,
    _utc_now,
)

logger = logging.getLogger("exa_demo.jobs")

# Module-level thread pool; small for pilot use.
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="job")


def submit_job(
    *,
    run_repo: RunRepository,
    artifact_store: ArtifactStore,
    workflow: str,
    mode: str,
    request_id: Optional[str],
    query_preview: Optional[str],
    run_fn: Callable[[], Dict[str, Any]],
    artifact_dir: Optional[str] = None,
    user_id: Optional[str] = None,
) -> RunRecord:
    """Enqueue a workflow job for background execution.

    Creates a RunRecord with status=queued, submits the work to
    the thread pool, and returns the record immediately.

    Args:
        run_repo: Repository for persisting job state.
        artifact_store: Store for uploading artifacts on completion.
        workflow: Workflow name (e.g. "research").
        mode: Execution mode ("smoke", "live", "auto").
        request_id: HTTP request ID from middleware.
        query_preview: Safe preview of the input query.
        run_fn: Zero-arg callable that executes the workflow and
                returns the payload dict.
        artifact_dir: Base directory for experiment artifacts.

    Returns:
        The queued RunRecord (check its ``id`` to poll status).
    """
    record = RunRecord(
        request_id=request_id,
        workflow=workflow,
        mode=mode,
        status="queued",
        started_at=_utc_now(),
        query_preview=_query_preview(query_preview),
        user_id=user_id,
    )
    run_repo.save(record)
    logger.info(
        "Job queued id=%s workflow=%s request_id=%s",
        record.id,
        workflow,
        request_id,
    )

    _executor.submit(
        _run_job,
        record_id=record.id,
        run_repo=run_repo,
        artifact_store=artifact_store,
        run_fn=run_fn,
        artifact_dir=artifact_dir,
    )
    return record


def _run_job(
    *,
    record_id: str,
    run_repo: RunRepository,
    artifact_store: ArtifactStore,
    run_fn: Callable[[], Dict[str, Any]],
    artifact_dir: Optional[str],
) -> None:
    """Execute a job in a worker thread."""
    # Transition to running.
    record = run_repo.get(record_id)
    if record is None:
        logger.error("Job record %s not found; aborting", record_id)
        return
    record.status = "running"
    run_repo.save(record)
    logger.info("Job running id=%s", record_id)

    t0 = time.monotonic()
    try:
        payload = run_fn()
        duration_ms = (time.monotonic() - t0) * 1000

        record.status = "completed"
        record.completed_at = _utc_now()
        record.duration_ms = round(duration_ms, 1)
        record.run_id = payload.get("run_id")
        record.cache_hit = payload.get("cache_hit")
        record.cost_summary = payload.get("summary") or None
        record.extra = {"result": payload}

        # Upload artifacts if available.
        if artifact_dir and record.run_id:
            from pathlib import Path

            art_dir = Path(artifact_dir) / record.run_id
            if art_dir.is_dir():
                try:
                    locations = artifact_store.upload_directory(
                        record.run_id, art_dir
                    )
                    record.artifact_count = len(locations)
                    record.artifact_location = str(art_dir)
                except Exception:
                    logger.exception(
                        "Failed to upload artifacts for job %s", record_id
                    )

        run_repo.save(record)
        logger.info(
            "Job completed id=%s duration_ms=%.1f", record_id, duration_ms
        )

    except Exception as exc:
        duration_ms = (time.monotonic() - t0) * 1000
        record.status = "failed"
        record.completed_at = _utc_now()
        record.duration_ms = round(duration_ms, 1)
        record.error_message = str(exc)[:500]
        run_repo.save(record)
        logger.exception("Job failed id=%s: %s", record_id, exc)
