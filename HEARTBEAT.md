# HEARTBEAT - exai-insurance-intel

_Generated file. Regenerate with `python scripts/generate_heartbeat.py`._

_Generated: 2026-04-12T02:14:21.887065+00:00_

## Current status
- Purpose: Exa-powered insurance intelligence toolkit for CAT-loss, claims, expert, contractor, and market/regulatory research workflows.
- Strategic role: Workflow engine plus controlled pilot web-product base for internal insurance-intelligence validation.
- Current milestone: Phase 5 Level 1 is partially complete: the thin FastAPI wrapper, frontend shell, and pilot auth/request-boundary hardening are shipped, and the persistence baseline is now the active next bounded slice.

## Operating posture
- Active Python workflow repo with package code in `src/exa_demo/`, a thin FastAPI app in the same package, and a Next.js frontend in `frontend/`. SQLite cache, budget controls, benchmark fixtures, exported artifacts, and smoke/live execution modes are already in place. Manual live validation is script-backed, but the inspected docs only verify smoke validation runs so far.

## Durable decisions
- Markdown docs under `docs/` remain the canonical backlog, architecture, ADR, and session-history surface for this repo.
- Existing CLI commands, artifact contracts, and smoke-first workflow expectations are stable and should be extended additively rather than rewritten.
- `smoke` stays the default mode for development, CI, and docs validation; `live` remains an explicit manual validation path that requires human review.
- The pilot web-product direction is private/internal first, with a thin FastAPI wrapper over existing workflows and a Next.js frontend in `frontend/`.
- Durable memory must stay curated and human-reviewed; heartbeat artifacts are generated sidecars, not the source of truth.

## Top blockers
- Phase 5 Level 1 is not complete because the persistence baseline is still missing; local SQLite is present, but the planned S3/Postgres pilot path is not yet implemented.
- GitHub issue numbering has drifted from the local Phase 5 roadmap IDs, so the tracker still has `TBD` GitHub URLs for those items until dedicated issues are created.
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
- Date: 2026-04-11e
- Objective: Take a simple end-of-session docs slice by syncing the local Phase 5 tracker and durable memory to the merged work.
- Changes made:
  - Inspected the local tracker, roadmap, heartbeat, and memory snapshot after the merged `#22` and first `#23` slices.
  - Marked the local Phase 5 `#22` tracker item as done and kept `#23` as the active next slice.
  - Updated the roadmap and `MEMORY.md` so they reflect that auth/request-boundary hardening is shipped and persistence is now the primary Phase 5 Level 1 blocker.
  - Documented the Phase 5 numbering drift: local tracker IDs `#19`-`#23` are roadmap/task IDs, while GitHub numbers `22` and `23` are already occupied by older merged PRs.
  - Added the session note and synced the tracker pointer for `#17`.
- Validation:
  - No code or test changes; docs-only sync.
- Open issues:
  - Dedicated GitHub issues still need to be created for the local Phase 5 tracker items if the repo wants live issue links instead of `TBD`.
  - `docs/pilot-architecture-decision.md` and the earlier pilot-alignment note still lag the shipped API/frontend reality.
- Decisions proposed:
  - Treat the local Phase 5 tracker IDs as internal roadmap IDs until dedicated GitHub issues are created, instead of linking them to unrelated GitHub numbers.
  - Keep the next coding work on `#23` persistence slices rather than reopening the completed `#22` boundary track.

## Next thin slice
- Continue `#23` with another small persistence-baseline seam, or end the session here if you want to wind down cleanly.
