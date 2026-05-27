# HEARTBEAT - exai-insurance-intel

_Generated file. Regenerate with `python scripts/generate_heartbeat.py`._

_Generated: 2026-05-27T02:17:01.818213+00:00_

## Current status
- Purpose: Exa-powered insurance intelligence toolkit for CAT-loss, claims, expert, contractor, and market/regulatory research workflows.
- Strategic role: Workflow engine plus controlled pilot web-product base for internal insurance-intelligence validation.
- Current milestone: Phase 5 Level 1 is partially complete: the thin FastAPI wrapper, frontend shell, and pilot auth/request-boundary hardening are shipped, and the persistence baseline is in progress with additive S3/Postgres adapters plus API health self-reporting for selected persistence backends.

## Operating posture
- Active Python workflow repo with package code in `src/exa_demo/`, a thin FastAPI app in the same package, and a Next.js frontend in `frontend/`. SQLite cache, budget controls, benchmark fixtures, exported artifacts, and smoke/live execution modes are already in place. Manual live validation is script-backed, but the inspected docs only verify smoke validation runs so far.

## Durable decisions
- Markdown docs under `docs/` remain the canonical backlog, architecture, ADR, and session-history surface for this repo.
- Existing CLI commands, artifact contracts, and smoke-first workflow expectations are stable and should be extended additively rather than rewritten.
- `smoke` stays the default mode for development, CI, and docs validation; `live` remains an explicit manual validation path that requires human review.
- The pilot web-product direction is private/internal first, with a thin FastAPI wrapper over existing workflows and a Next.js frontend in `frontend/`.
- Durable memory must stay curated and human-reviewed; heartbeat artifacts are generated sidecars, not the source of truth.

## Top blockers
- Phase 5 Level 1 is not complete because the persistence baseline still lacks end-to-end S3/Postgres-backed pilot validation and deployment posture; local defaults, pilot adapters, and backend self-reporting are present.
- GitHub issue numbering has drifted from the local Phase 5 roadmap IDs, so the tracker still has `TBD` GitHub URLs for those items until dedicated issues are created.
- Live Exa mode, S3/Postgres-backed runtime behavior, and deployed pilot environments remain unvalidated; the documented validated path is still local smoke mode.

## Docs + setup
- Docs freshness: Workable. `README.md`, `docs/local-validation.md`, `docs/roadmap.md`, `docs/issue-tracker.md`, `docs/integration-boundaries.md`, and `docs/pilot-architecture-decision.md` reflect the current smoke/local and persistence-in-progress posture; older March session notes remain historical and may describe pre-slice state.
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
- Date: 2026-05-26
- Objective: Harden Exa 2026 request-shape drift before continuing with cost-model and grounding work.
- Changes made:
  - Stopped emitting `startCrawlDate` and `endCrawlDate` from find-similar payloads while keeping the Python kwargs as deprecated no-ops.
  - Expanded payload/API/CLI tests so request payloads reject `livecrawl`, `highlightsPerUrl`, `numSentences`, `startCrawlDate`, and `endCrawlDate`.
  - Replaced README `--livecrawl` examples with `--freshness always-live` / `--max-age-hours 0` freshness language.
  - Added ADR-0002 for the Exa 2026 request modernization boundary.
  - Updated roadmap, issue tracker, demo gallery, integration boundaries, and session notes to describe user-facing `research` as `/search` with `type="deep-reasoning"`.
  - Documented the next cost/grounding gap without claiming live pricing, S3, Postgres, frontend, or deployed validation.
- Validation:
  - `python -m pytest -q tests/test_client.py tests/test_workflow_builders.py tests/test_api.py tests/test_cli.py` -> passed (`65 passed`)
  - `python -m ruff check .` -> passed
  - `python -m pytest -q` -> passed (`277 passed`, one Jupyter path deprecation warning)
  - `python scripts/run_live_validation.py --mode smoke` -> passed
  - Current smoke-validation artifacts from `live-validation-20260527T021418Z-*` had no deprecated-field matches
- Open issues:
  - Cost-model estimates still need a dedicated follow-up against current Exa pricing for search-backed `research`, `/answer`, and `/findSimilar`.
  - Modern grounding metadata should be normalized consistently across artifacts in the next grounding slice.
  - Live Exa, S3, Postgres, frontend, and deployed validation were not run in this cleanup.
- Decisions proposed:
  - Keep public workflow names and artifact filenames stable while updating request payload shapes underneath.
  - Keep find-similar crawl-date kwargs as compatibility no-ops rather than removing them abruptly.
  - Treat `research` as a repo workflow name, not evidence of a current Exa `/research` transport endpoint.

## Next thin slice
- Reconcile the cost model against current Exa pricing and modern grounding metadata, with smoke tests first and live validation only as an explicit manual step.
