# HEARTBEAT - exai-insurance-intel

_Generated file. Regenerate with `python scripts/generate_heartbeat.py`._

_Generated: 2026-03-27T20:47:18.625729+00:00_

## Current status
- Purpose: Exa-powered insurance intelligence toolkit for CAT-loss, claims, expert, contractor, and market/regulatory research workflows.
- Strategic role: Workflow engine plus controlled pilot web-product base for internal insurance-intelligence validation.
- Current milestone: Phase 5 Level 1 is partially complete: the thin FastAPI wrapper and frontend shell are shipped, while pilot auth/request controls and persistence baseline remain the next bounded slices.

## Operating posture
- Active Python workflow repo with package code in `src/exa_demo/`, a thin FastAPI app in the same package, and a Next.js frontend in `frontend/`. SQLite cache, budget controls, benchmark fixtures, exported artifacts, and smoke/live execution modes are already in place. Manual live validation is script-backed, but the inspected docs only verify smoke validation runs so far.

## Durable decisions
- Markdown docs under `docs/` remain the canonical backlog, architecture, ADR, and session-history surface for this repo.
- Existing CLI commands, artifact contracts, and smoke-first workflow expectations are stable and should be extended additively rather than rewritten.
- `smoke` stays the default mode for development, CI, and docs validation; `live` remains an explicit manual validation path that requires human review.
- The pilot web-product direction is private/internal first, with a thin FastAPI wrapper over existing workflows and a Next.js frontend in `frontend/`.
- Durable memory must stay curated and human-reviewed; heartbeat artifacts are generated sidecars, not the source of truth.

## Top blockers
- Phase 5 Level 1 is not complete because auth, request-boundary controls, rate limiting, and request logging are still the next slice in `docs/issue-tracker.md`.
- Pilot persistence baseline is still missing; local SQLite is present, but the planned S3/Postgres pilot path is not yet implemented.
- Docs freshness is mixed because `docs/pilot-architecture-decision.md` and `docs/sessions/2026-03-22-pilot-alignment.md` still describe a pre-slice state with no frontend/API layer, while README and later slice notes show both shipped.

## Docs + setup
- Docs freshness: Mixed but workable. `README.md`, `docs/roadmap.md`, `docs/issue-tracker.md`, `docs/integration-boundaries.md`, and the 2026-03-22 implementation session notes reflect the current repo direction; the pilot architecture doc's current-state section and the pilot-alignment note lag behind the shipped API/frontend reality.
- Setup friction: Moderate. Python setup is straightforward, but full local work spans Python deps, optional `[api]` extras, a separate `frontend/` npm install and env file, and deliberate handling of smoke versus live mode with `EXA_API_KEY` only for bounded manual validation.

## Validation path
- `python -m ruff check .`
- `python -m pytest -q`
- `python scripts/run_live_validation.py --mode smoke`
- `uvicorn exa_demo.api:app --reload`
- `cd frontend` then `npm install`, copy `.env.local.example` to `.env.local`, and run `npm run dev`

## Key files / commands
- `README.md`
- `docs/roadmap.md`
- `docs/issue-tracker.md`
- `docs/integration-boundaries.md`
- `docs/pilot-architecture-decision.md`
- `docs/agent-execution-defaults.md`
- `docs/sessions/2026-03-22-pilot-alignment.md`
- `docs/sessions/2026-03-22-api-wrapper.md`
- `docs/sessions/2026-03-22-frontend-shell.md`
- `scripts/run_live_validation.py`
- `scripts/run_notebook_smoke.py`

## Safe automation now
- Regenerate `HEARTBEAT.md` and `heartbeat.json` from `MEMORY.md` plus the latest `memory/*.md` session file only.
- Append factual session memory after bounded work that actually happened in this repo.
- Use smoke-mode checks and doc inspection to refresh generated current-state summaries without changing durable docs automatically.

## Wait until later
- Any automatic promotion of generated heartbeat output into durable memory or strategy docs.
- Scheduled or automatic live validation runs, dashboards, or cross-repo telemetry.
- Scope beyond this scaffold into auth redesign, persistence implementation, async jobs, deployment, infra, or broader docs refactors.

## Last session
- Date: 2026-03-27a
- Objective: Close the smallest real multi-user data-isolation gap by enforcing owner-or-ops authorization on single-record run/job read routes and validate the change with focused API tests.
- Changes made:
  - Inspected `src/exa_demo/api.py`, `src/exa_demo/api_auth.py`, `src/exa_demo/persistence.py`, `tests/test_api.py`, and `tests/test_api_auth.py` to confirm the single-record read gap and existing auth patterns.
  - Added `require_owner_or_ops_access(...)` in `src/exa_demo/api_auth.py` as a minimal helper for already-fetched run records.
  - Applied the helper to `GET /api/research/jobs/{job_id}` and `GET /api/runs/{record_id}` in `src/exa_demo/api.py`.
  - Chose `404` for non-owner non-ops single-record reads so the API does not reveal whether another user's record exists.
  - Added six focused multi-user tests in `tests/test_api_auth.py` covering owner, non-owner, and ops access for both research-job and run-record reads.
  - Added a focused session log in `docs/sessions/2026-03-27-single-record-owner-or-ops-auth.md`.
- Validation:
  - Ran `python -m pytest tests/test_api_auth.py -q` and confirmed `21 passed`.
  - Ran `python -m pytest tests/test_api.py -q` and confirmed `9 passed`.
  - Ran `python -m ruff check src/exa_demo/api.py src/exa_demo/api_auth.py tests/test_api_auth.py` and confirmed all checks passed.
- Open issues:
  - Single-record reads for legacy `RunRecord` rows with `user_id = null` now require ops access because ownership cannot be proven.
  - This slice intentionally did not audit or redesign any other auth surfaces beyond `GET /api/research/jobs/{job_id}` and `GET /api/runs/{record_id}`.
- Decisions proposed:
  - Keep single-record authorization logic as a narrow helper in `api_auth.py` instead of pushing ownership checks into persistence for this slice.
  - Use `404` rather than `403` for non-owner access to per-record reads so record existence is not disclosed across users.

## Next thin slice
- Audit whether any other single-record endpoints return user-owned data without an owner-or-ops check.
- Decide separately whether legacy `user_id = null` records need a migration/backfill or should remain ops-only.
