# HEARTBEAT - exai-insurance-intel

_Generated file. Regenerate with `python scripts/generate_heartbeat.py`._

_Generated: 2026-04-12T02:08:08.666053+00:00_

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
- Date: 2026-04-11d
- Objective: Start `#23` with a narrow persistence fix so stored artifact locations reflect the actual backend location after upload.
- Changes made:
  - Inspected `persist_workflow_run(...)` in `src/exa_demo/persistence.py` and `_run_job(...)` in `src/exa_demo/jobs.py` and confirmed both stored local experiment paths after artifact upload.
  - Added `run_location(run_id)` to the artifact-store contract and implemented it for both `LocalArtifactStore` and `S3ArtifactStore`.
  - Updated the sync persistence helper and async job runner to persist the artifact-store location instead of the source directory when uploads succeed.
  - Added focused coverage for local-store run locations, S3-store run locations, persisted S3 artifact locations, and async job artifact-location persistence.
  - Synced the local tracker/session pointers for this first `#23` slice.
- Validation:
  - Ran `python -m pytest -q tests/test_persistence.py tests/test_jobs.py` and confirmed `54 passed`.
  - Ran `python -m ruff check src/exa_demo/persistence.py src/exa_demo/jobs.py tests/test_persistence.py tests/test_jobs.py` and confirmed all checks passed.
- Open issues:
  - This slice did not add live S3 or Postgres integration coverage; it only tightened the backend-location contract around the existing abstractions.
  - The repo still needs more thin `#23` slices before cloud-backed persistence is operationally well pinned.
- Decisions proposed:
  - Treat stored artifact locations as canonical store references so later pilot surfaces can dereference artifacts without guessing whether a run used local or S3-backed storage.
  - Keep `#23` additive and test-first by tightening one persistence contract at a time instead of attempting a broad rollout.

## Next thin slice
- Add one more thin `#23` slice around persistence factory success paths or a small Postgres/S3 seam that can be verified without live infrastructure.
