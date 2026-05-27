# HEARTBEAT - exai-insurance-intel

_Generated file. Regenerate with `python scripts/generate_heartbeat.py`._

_Generated: 2026-05-27T20:11:07.891614+00:00_

## Current status
- Purpose: Exa-powered insurance intelligence toolkit for CAT-loss, claims, expert, contractor, and market/regulatory research workflows.
- Strategic role: Workflow engine plus controlled pilot web-product base for internal insurance-intelligence validation.
- Current milestone: Phase 5 Level 1 is partially complete: the thin FastAPI wrapper, frontend shell, and pilot auth/request-boundary hardening are shipped, and the persistence baseline is in progress with additive S3/Postgres adapters plus API health self-reporting for selected persistence backends.

## Operating posture
- Active Python workflow repo with package code in `src/exa_demo/`, a thin FastAPI app in the same package, and a Next.js frontend in `frontend/`. SQLite cache, budget controls, benchmark fixtures, exported artifacts, and smoke/live execution modes are already in place. Manual live validation is script-backed. The latest bounded live evidence covers only CLI `research` and `structured-search` grounding behavior; the broader local UI path remains smoke/mock.

## Durable decisions
- Markdown docs under `docs/` remain the canonical backlog, architecture, ADR, and session-history surface for this repo.
- Existing CLI commands, artifact contracts, and smoke-first workflow expectations are stable and should be extended additively rather than rewritten.
- `smoke` stays the default mode for development, CI, and docs validation; `live` remains an explicit manual validation path that requires human review.
- The pilot web-product direction is private/internal first, with a thin FastAPI wrapper over existing workflows and a Next.js frontend in `frontend/`.
- Durable memory must stay curated and human-reviewed; heartbeat artifacts are generated sidecars, not the source of truth.

## Top blockers
- Phase 5 Level 1 is not complete because the persistence baseline still lacks end-to-end S3/Postgres-backed pilot validation and deployment posture; local defaults, pilot adapters, and backend self-reporting are present.
- GitHub issue numbering has drifted from the local Phase 5 roadmap IDs, so the tracker still has `TBD` GitHub URLs for those items until dedicated issues are created.
- Broad live Exa behavior, S3/Postgres-backed runtime behavior, frontend live mode, and deployed pilot environments remain unvalidated. A bounded 2026-05-27 live CLI rerun did validate `research` and `structured-search` grounding behavior only.

## Docs + setup
- Docs freshness: Workable. `README.md`, `docs/local-validation.md`, `docs/roadmap.md`, `docs/issue-tracker.md`, `docs/integration-boundaries.md`, and `docs/pilot-architecture-decision.md` reflect the current smoke/local, bounded live grounding, and persistence-in-progress posture; older March session notes remain historical and may describe pre-slice state.
- Setup friction: Moderate. Python setup is straightforward, but full local work spans Python deps, optional `[api]` extras, a separate `frontend/` npm install and env file, and deliberate handling of smoke versus live mode with `EXA_API_KEY` only for bounded manual validation.

## Validation path
- `python -m ruff check .`
- `python -m pytest -q`
- `python scripts/run_live_validation.py --mode smoke`
- `uvicorn exa_demo.api:app --reload`
- `cd frontend` then `npm install`, copy `.env.local.example` to `.env.local`, and run `npm run dev`

## Key files / commands
- `README.md`
- `docs/local-validation.md`
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
- Scope beyond this scaffold into auth redesign, persistence redesign, async jobs, deployment, infra, or broader docs refactors.

## Last session
- Date: 2026-05-27
- Objective: Sync repo docs/status after the Exa 2026 modernization, cost-model reconciliation, and bounded live grounding validation.
- Changes made:
  - Updated the 2026-05-27 live grounding session note to record the successful rerun after the placeholder Exa API key was replaced.
  - Reconciled roadmap and issue-tracker status so `#51` and `#56` are closed/completed instead of future follow-up work.
  - Updated ADR-0002 and validation boundary docs to distinguish smoke validation from the bounded live CLI rerun.
  - Kept the status sync docs-only; no app code, tests, frontend, persistence, deployment, or live Exa calls were changed or run during the sync.
- Validation:
  - `python -m ruff check .` -> passed.
  - `python -m pytest -q` -> passed (`299 passed`, one existing Jupyter path deprecation warning).
  - `python scripts/run_live_validation.py --mode smoke` -> passed and wrote smoke artifacts under `live-validation-artifacts/`.
  - `git diff --check` -> passed.

## Next thin slice
- Continue Phase 5 Level 1 persistence work without widening into deployment or broad infra redesign.
