# Session: Thin FastAPI Wrapper (Pilot Slice 1)

- Date: 2026-03-22
- Participants: Claude Code (Opus 4.6)
- Related roadmap items: Phase 5 Level 1, #20
- Related ADRs: docs/pilot-architecture-decision.md

## Context

First coding slice for the pilot web product layer. The goal was to expose existing workflow functions as HTTP endpoints so a frontend shell can call them next.

## Repo Facts Observed

- All 5 target workflows (search, answer, research, find-similar, structured-search) have clean `run_*_workflow` functions that accept `(config, pricing, runtime, runtime_metadata)` and return JSON-serializable dicts.
- `resolve_runtime` copies `os.environ` into a dict (no side effects on global state), making it safe for concurrent API use.
- `structured-search` workflow expects a file path for the schema; API wraps this with a temp file.
- Existing tests use `tmp_path` for artifact dirs and sqlite paths — same pattern works for API tests.

## Decisions Made

- **FastAPI in `[api]` optional dep group** — CLI users don't need FastAPI; `[dev]` pulls it in via self-reference.
- **All endpoints default to smoke mode** — safe for frontend dev without API key.
- **Pydantic request/response models** — typed contracts for frontend consumption.
- **Temp file for structured-search schema** — avoids modifying existing workflow; schema passes as inline JSON in request body.
- **Module-level `ARTIFACT_DIR`** — simple override point for tests; dependency injection not needed at pilot scale.

## Issues Opened or Updated

- `#20` Thin FastAPI wrapper — status changed from Next to Done.

## Docs Touched

- `README.md` — Added API server section, feature matrix row, updated "What This Repo Is Today"
- `docs/roadmap.md` — Thin API wrapper moved to Done
- `docs/issue-tracker.md` — #20 status updated, slice 1 marked done in Next Coding Slices

## Files Created

- `src/exa_demo/api.py` — FastAPI app with 6 endpoints (health + 5 workflows)
- `tests/test_api.py` — 9 smoke-mode tests

## Files Modified

- `pyproject.toml` — Added `[api]` optional deps (fastapi, uvicorn), httpx to dev deps

## Tests and Checks Run

- `python -m ruff check .` — All checks passed
- `python -m pytest -q` — 107 passed (98 existing + 9 new)
- `python -m pytest tests/test_api.py -v` — 9/9 passed

## Outcome

Slice 1 complete. The API server runs locally via `uvicorn exa_demo.api:app --reload` and serves JSON endpoints for all 5 target workflows in smoke mode. Interactive docs at `/docs`. All tests pass.

## Next-Session Handoff

Next slice: **Frontend app shell** (`#21`)
- Next.js 14+ scaffold in `frontend/` with App Router, TypeScript, Tailwind, shadcn/ui
- Landing page, search form, results display
- Calls the FastAPI endpoints added in this session
- Deploy target: Vercel

The API response shapes are defined by the Pydantic models in `src/exa_demo/api.py` — the frontend should consume these directly.
