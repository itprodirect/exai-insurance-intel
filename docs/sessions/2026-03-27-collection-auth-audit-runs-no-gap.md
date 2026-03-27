# Session: Collection Auth Audit (`GET /api/runs`) No-Gap Closeout

- Date: 2026-03-27
- Participants: Codex (GPT-5)
- Related scope: collection/list auth boundary for persisted run history

## Context

Inspect exactly one collection/list auth boundary that could expose user-owned data across accounts and patch at most one confirmed gap.

## Inspection Targets

- `src/exa_demo/api.py`: `api_list_runs`
- `src/exa_demo/persistence.py`: `list_runs`
- `src/exa_demo/api_auth.py`: `require_ops_access`
- `tests/test_users.py`: adjacent `/api/runs` auth coverage

## Findings

- `GET /api/runs` exists and is the highest-risk collection route because it returns persisted run history that is not `/me/...` scoped.
- `api_list_runs` calls `require_ops_access(request)` before invoking `run_repo.list_runs(...)`.
- The repository `list_runs(...)` call itself is intentionally unscoped for this route and can return cross-user data, but only after the route-level ops gate passes.
- Adjacent auth tests already prove the intended boundary:
  - allowlisted ops user can read the global `/api/runs` collection
  - non-ops user receives `403` on `/api/runs`

## Decision

- No confirmed auth gap remains for the inspected `GET /api/runs` boundary in the current branch state.
- Stop without editing API, auth, or persistence code.

## Validation

- `python -m pytest tests/test_users.py -q -k "allowlisted_ops_user_sees_all_runs or non_ops_user_cannot_access_global_runs"` -> passed (`2 passed, 22 deselected`)

## Recommended Next Task

- Inspect exactly one other non-`/me` collection boundary only if it currently returns user-owned data and is not already obviously ops-only.
