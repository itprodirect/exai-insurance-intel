# Session: Issue 23 persistence health posture

- Date: 2026-04-28
- Participants: Codex, user
- Related roadmap items: `#17`, `#23`
- Related ADRs: none

## Context

Close the session after a narrow Phase 5 persistence-baseline slice that makes the API process report which run and artifact persistence backends it selected.

## Repo Facts Observed

- The worktree was already on `codex/issue-17-local-smoke-doc-sync`.
- `src/exa_demo/api.py` now returns `run_store` and `artifact_store` from `/health` and `/api/health`.
- The health endpoint remains unauthenticated when bearer auth is enabled.
- `src/exa_demo/persistence.py` now logs selected local, Postgres, local artifact, and S3 artifact factory backends.
- `.env.example` now documents optional pilot persistence env vars.
- `pyproject.toml` now exposes optional `postgres`, `s3`, and aggregate `pilot` extras.
- The current change remains a local/tested posture slice; it does not deploy or live-validate S3/Postgres infrastructure.

## Decisions Made

- Keep this as a narrow `#23` persistence-baseline posture slice.
- Keep `/health` open and use it to expose backend labels only, not secrets or connection strings.
- Record the final closeout in session notes, memory, tracker pointers, and regenerated heartbeat sidecars.

## Issues Opened or Updated

- `#17 Maintain roadmap, issue tracker, ADRs, and session notes` - advanced with final closeout docs.
- Local tracker item `#23` - advanced with API health backend labels, factory logging, optional pilot dependency extras, and env documentation.

## Docs Touched

- `README.md`
- `docs/local-validation.md`
- `docs/issue-tracker.md`
- `docs/roadmap.md`
- `MEMORY.md`
- `memory/2026-04-28.md`
- `docs/sessions/2026-04-28-issue-23-persistence-health-posture.md`
- `HEARTBEAT.md`
- `heartbeat.json`

## Tests and Checks Run

- `python -m ruff check src/exa_demo/api.py src/exa_demo/persistence.py tests/test_api.py tests/test_api_auth.py` -> passed
- `python -m pytest -q tests/test_api.py tests/test_api_auth.py` -> passed (`31 passed`)
- `python -m pytest -q tests/test_persistence.py` -> passed (`62 passed`)

## Outcome

- The API health response now reports the selected run and artifact backends while preserving unauthenticated health access.
- Optional pilot persistence dependency groups and env knobs are documented for future pilot setup.
- The final docs pass records that `#23` remains in progress and still needs explicit S3/Postgres-backed end-to-end validation before claiming pilot durability.

## Next-Session Handoff

- Continue `#23` with one more narrow persistence-baseline slice, preferably an integration seam that validates configured Postgres/S3 behavior without broad deployment work.
- Keep deployment, migrations, and auth redesign out of scope unless explicitly requested.
