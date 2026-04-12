# Session: Issue 22 rate-limit scope isolation

- Date: 2026-04-11
- Participants: Codex, user
- Related roadmap items: `#22`, `#17`
- Related ADRs: none

## Context

Take the thinnest evidence-backed auth/request-boundary slice inside `#22` by inspecting the shipped pilot API controls and hardening one real multi-user gap without redesigning auth.

## Repo Facts Observed

- `src/exa_demo/api_auth.py` already shipped bearer auth, ops allowlisting, mode/query guards, request logging, and a rate limiter.
- The current limiter keyed all requests by client IP, even in multi-user mode after bearer auth had already resolved a concrete `user_id`.
- `tests/test_api_auth.py` covered limit enforcement in single-key mode but did not verify isolation between different authenticated users.

## Decisions Made

- Keep the rate limiter behavior unchanged for single-key and no-auth modes by preserving the existing per-IP buckets there.
- In multi-user mode only, key the limiter by resolved authenticated user ID so one user's traffic cannot consume another user's allowance when they share a client IP.
- Stop after this one boundary fix rather than broadening into auth redesign, persistence, or UI work.

## Issues Opened or Updated

- `#22 Pilot auth + request/budget boundary controls` — advanced with a narrow multi-user rate-limit isolation fix and updated local tracker pointer.
- `#17 Maintain roadmap, issue tracker, ADRs, and session notes` — updated indirectly through required session/memory/heartbeat sync.

## Docs Touched

- `docs/security.md`
- `docs/issue-tracker.md`
- `docs/sessions/2026-04-11-issue-22-rate-limit-scope.md`

## Tests and Checks Run

- `python -m pytest -q tests/test_api_auth.py` -> passed (`22 passed`)
- `python -m ruff check src/exa_demo/api_auth.py tests/test_api_auth.py` -> passed

## Outcome

- Hardened the pilot API rate limiter so multi-user deployments isolate request quotas per authenticated user instead of sharing a single IP bucket.
- Added focused regression coverage for the new behavior.
- Kept the change additive and limited to the auth/request-boundary layer.

## Next-Session Handoff

- If `#22` continues, the next similarly thin slice is to inspect one more request-boundary gap such as saved-query input validation or run-list pagination bounds.
- The larger follow-on after auth/request hardening remains `#23` persistence/state baseline, but only after the boundary slice is considered sufficient.
