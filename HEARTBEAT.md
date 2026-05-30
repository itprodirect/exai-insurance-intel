# HEARTBEAT - exai-insurance-intel

_Generated file. Regenerate with `python scripts/generate_heartbeat.py`._

_Generated: 2026-05-29T23:40:31.112725+00:00_

## Current status
- Purpose: Exa-powered insurance intelligence toolkit for CAT-loss, claims, expert, contractor, and market/regulatory research workflows.
- Strategic role: Workflow engine plus controlled pilot web-product base for internal insurance-intelligence validation.
- Current milestone: Phase 5 Level 1 is partially complete: the thin FastAPI wrapper, frontend shell, and pilot auth/request-boundary hardening are shipped, and the persistence baseline is in progress with additive S3/Postgres adapters, API health self-reporting for selected persistence backends, and a bounded real-service S3/Postgres validation command.

## Operating posture
- Active Python workflow repo with package code in `src/exa_demo/`, a thin FastAPI app in the same package, and a Next.js frontend in `frontend/`. SQLite cache, budget controls, benchmark fixtures, exported artifacts, and smoke/live execution modes are already in place. Manual live validation is script-backed. The latest bounded live evidence covers only CLI `research` and `structured-search` grounding behavior; the broader local UI path remains smoke/mock.

## Durable decisions
- Markdown docs under `docs/` remain the canonical backlog, architecture, ADR, and session-history surface for this repo.
- Existing CLI commands, artifact contracts, and smoke-first workflow expectations are stable and should be extended additively rather than rewritten.
- `smoke` stays the default mode for development, CI, and docs validation; `live` remains an explicit manual validation path that requires human review.
- The pilot web-product direction is private/internal first, with a thin FastAPI wrapper over existing workflows and a Next.js frontend in `frontend/`.
- Durable memory must stay curated and human-reviewed; heartbeat artifacts are generated sidecars, not the source of truth.

## Top blockers
- Phase 5 Level 1 is not complete because the persistence baseline still lacks actual external S3/Postgres-backed pilot evidence and deployment posture; local defaults, pilot adapters, backend self-reporting, and a bounded validation command are present.
- GitHub issue numbering has drifted from the local Phase 5 roadmap IDs, so the tracker still has `TBD` GitHub URLs for those items until dedicated issues are created.
- Broad live Exa behavior, real S3/Postgres-backed runtime behavior, frontend live mode, and deployed pilot environments remain unvalidated unless the bounded validation command is run against real services. A bounded 2026-05-27 live CLI rerun did validate `research` and `structured-search` grounding behavior only.

## Docs + setup
- Docs freshness: Workable. `README.md`, `docs/local-validation.md`, `docs/roadmap.md`, `docs/issue-tracker.md`, `docs/integration-boundaries.md`, and `docs/pilot-architecture-decision.md` reflect the current smoke/local, bounded live grounding, and persistence-in-progress posture with a real-service S3/Postgres validation command; older March session notes remain historical and may describe pre-slice state.
- Setup friction: Moderate. Python setup is straightforward, but full local work spans Python deps, optional `[api]` extras, a separate `frontend/` npm install and env file, and deliberate handling of smoke versus live mode with `EXA_API_KEY` only for bounded manual validation.

## Validation path
- `python -m ruff check .`
- `python -m pytest -q`
- `python scripts/run_live_validation.py --mode smoke`
- `python scripts/run_pilot_persistence_validation.py --output live-validation-artifacts/pilot-s3-postgres-validation.json` only in an environment with real Postgres, S3, and AWS credentials
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
- `scripts/run_pilot_persistence_validation.py`
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
- Date: 2026-05-29
- Objective: Add a bounded, repeatable validation path for the pilot S3/Postgres persistence baseline without adding infrastructure, deployment setup, migration redesign, or fake evidence.
- Changes made:
  - Added `scripts/run_pilot_persistence_validation.py` and `src/exa_demo/pilot_persistence_validation.py`.
  - The command requires `PILOT_RUN_STORE=postgres`, `PILOT_POSTGRES_URL`, `PILOT_ARTIFACT_STORE=s3`, `PILOT_S3_BUCKET`, and a validation-scoped `PILOT_S3_PREFIX`.
  - The command starts the FastAPI app unless `--base-url` is provided, runs one smoke `/api/search`, verifies `/health` reports `postgres` and `s3`, reads the matching run through `/api/me/runs`, verifies the persisted S3 artifact location/count, and lists the S3 prefix with `boto3`.
  - Added focused tests for validation guardrails in `tests/test_persistence.py`.
  - Updated `.env.example`, `docs/local-validation.md`, `docs/integration-boundaries.md`, `docs/roadmap.md`, `docs/issue-tracker.md`, and the session log.
- Validation:
  - `python -m ruff check src/exa_demo/pilot_persistence_validation.py scripts/run_pilot_persistence_validation.py tests/test_persistence.py` -> passed during implementation.
  - `python -m ruff check .` -> passed.
  - `python -m pytest -q tests/test_persistence.py tests/test_api.py tests/test_api_auth.py` -> passed (`105 passed`).
  - Real S3/Postgres validation was not run because required external config and credential hints were not present in the environment.
- Open issues:
  - Real external S3/Postgres validation was not claimed unless the command exits `0` against real services.
  - The command exits `2` when required external persistence configuration is missing or still local-only.
- Decisions proposed:
  - Keep the path smoke-mode for Exa traffic and real for persistence.
  - Keep the external command out of default CI because it requires Postgres, S3, and AWS credentials.

## Next thin slice
- Run the bounded validation command in a credentialed pilot environment and attach/review the JSON evidence.
