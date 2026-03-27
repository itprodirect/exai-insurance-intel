# Session: Mutation Auth Audit - Saved Query Delete

- Date: 2026-03-27
- Participants: Codex (GPT-5)
- Related scope: single-record mutation auth boundary

## Context

Inspect exactly one single-record mutation route involving user-owned data and patch at most one confirmed auth gap.

## Route Inspected

- `DELETE /api/me/saved-queries/{query_id}`

## Findings

- The route resolves the current user with `get_current_user(request)`.
- The route delegates deletion to `run_repo.delete_saved_query(query_id, uid)`.
- The repository delete is explicitly scoped by both query id and user id: `DELETE FROM saved_queries WHERE id = ? AND user_id = ?`.
- Existing tests already cover:
  - owner can delete own saved query
  - deleting a missing saved query returns `404`
  - a different user cannot delete another user's saved query
  - repository-level wrong-user delete returns `False`

## Decision

- No confirmed auth gap remains for this inspected mutation boundary.
- Per the slice rules, stop without editing API/auth code.

## Validation

- `python -m pytest tests/test_users.py -q -k "delete_saved_query or delete_not_found or user_cannot_delete_others_query or delete_wrong_user"` -> passed (`4 passed, 20 deselected`)

## Recommended Next Task

- Audit one other single-record mutation boundary only if it is clearly user-owned and ID-addressable, for example a future job cancel/delete or record rerun endpoint if one is added.
