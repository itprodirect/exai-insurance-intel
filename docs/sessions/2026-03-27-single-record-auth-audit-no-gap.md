# Session: Single-Record Auth Audit (No Confirmed Gap)

- Date: 2026-03-27
- Participants: Codex (GPT-5)
- Related scope: single-record run/job read auth boundary

## Context

Inspect only the current auth boundary around single-record run/job reads and patch at most one confirmed gap.

## Inspection Targets

- `src/exa_demo/api.py`: `api_get_research_job`
- `src/exa_demo/api.py`: `api_get_run`
- `src/exa_demo/jobs.py`: internal `run_repo.get` usage
- `tests/test_api_auth.py`: current auth coverage for research jobs, run reads, and ops summary

## Findings

- `api_get_research_job` already enforces `require_owner_or_ops_access(...)` after fetching the record and before returning it.
- `api_get_run` already enforces `require_owner_or_ops_access(...)` after fetching the record and before returning it.
- The existing tests already cover:
  - owner read of own research job
  - non-owner denial for another user's research job
  - ops read of another user's research job
  - owner read of own run record
  - non-owner denial for another user's run record
  - ops read of another user's run record
  - ops summary allow/deny behavior
- `src/exa_demo/jobs.py` uses `run_repo.get(record_id)` only inside the worker thread to update queued job state; this is not a user-facing read route and is outside the inspected auth boundary.

## Decision

- No confirmed single-record auth gap remains in the inspected boundary.
- Per the decision rule, stop without editing API/auth code.

## Validation

- `python -m pytest tests/test_api_auth.py -q -k "research_job or run_record or ops_allowed_for_default_internal_user or ops_forbidden_for_non_allowlisted_user"` -> passed (`8 passed, 13 deselected`)
- `python -m pytest tests/test_api_auth.py -q` -> passed (`21 passed`)

## Recommended Next Task

- Take a tiny repo-process slice: add a short code-review checklist item or PR template note that single-record user-owned reads must explicitly enforce `owner OR ops` authorization and include one cross-user test per route.
