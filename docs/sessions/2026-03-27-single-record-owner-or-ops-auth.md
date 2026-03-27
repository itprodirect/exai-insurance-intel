# Session: Single-Record Owner-Or-Ops Read Authorization

- Date: 2026-03-27
- Participants: Codex (GPT-5)
- Related roadmap items: Phase 5 Level 1 auth/request controls
- Related files: `src/exa_demo/api.py`, `src/exa_demo/api_auth.py`

## Context

Close the smallest real multi-user data-isolation gap in the pilot API by enforcing owner-or-ops authorization on the two single-record run/job read routes without redesigning auth or changing existing happy-path behavior.

## Findings Before Changes

- `GET /api/research/jobs/{job_id}` fetched `run_repo.get(job_id)` and returned the record with no ownership check.
- `GET /api/runs/{record_id}` fetched `run_repo.get(record_id)` and returned the record with no ownership check.
- `/api/runs` was already protected by `require_ops_access`.
- `/api/me/runs` was already scoped by `user_id`.
- Existing tests covered ops-only access for aggregate run surfaces, but not cross-user access for these single-record reads.

## Decision

- Add one narrow helper in `api_auth.py` for `owner OR ops` access to an already-fetched record.
- Return `404` for non-owner non-ops access on single-record lookups so the API does not reveal whether another user's record exists.
- Leave ops/admin aggregate surfaces on their current explicit `403` behavior.

## Changes Made

- Added `require_owner_or_ops_access(request, owner_user_id, *, not_found_detail=...)` in `src/exa_demo/api_auth.py`.
- Applied that helper to:
  - `api_get_research_job`
  - `api_get_run`
- Preserved existing success responses for owners and ops users.
- Added focused multi-user tests covering:
  - owner read of own research job
  - non-owner denial for another user's research job
  - ops read of another user's research job
  - owner read of own run record
  - non-owner denial for another user's run record
  - ops read of another user's run record

## Validation

- `python -m pytest tests/test_api_auth.py -q` -> passed (`21 passed`)
- `python -m pytest tests/test_api.py -q` -> passed (`9 passed`)
- `python -m ruff check src/exa_demo/api.py src/exa_demo/api_auth.py tests/test_api_auth.py` -> passed

## Risks / Follow-Up

- Legacy run records with `user_id = null` are now effectively ops-only on these single-record routes. That is the safer behavior for unowned records, but older data without owner attribution may no longer be readable by non-ops users.
- This slice only closes the confirmed read gap on the two single-record routes. It does not audit other record-oriented endpoints beyond the ones named above.
