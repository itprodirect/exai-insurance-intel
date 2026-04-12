# Session: Issue 17 docs truth sync

- Date: 2026-04-12
- Participants: Codex, user
- Related roadmap items: `#17`, `#23`
- Related ADRs: none

## Context

Take a narrow docs-only governance slice after the latest Phase 5 merges so the top-level docs match the live repo state on `main`.

## Repo Facts Observed

- PR #37 landed the first `#23` persistence slice for artifact-location persistence.
- PR #38 landed the prior `#17` tracker sync that already marked local Phase 5 `#22` as done.
- PR #39 landed targeted Postgres repository and factory success-path coverage for the persistence baseline.
- `README.md` still claimed there was no authentication or multi-user support and still framed persistence as local-only SQLite.
- `docs/pilot-architecture-decision.md` still described the repo as having no web frontend and no HTTP API layer.
- `docs/issue-tracker.md` still described local Phase 5 `#23` as an untouched next slice instead of an in-progress baseline.
- `docs/roadmap.md` was checked and already reflected local Phase 5 `#22` as done and `#23` as current, so it did not need changes.

## Decisions Made

- Keep this as a docs-only truth-sync under `#17`.
- Update the README so it acknowledges the shipped pilot auth/request-boundary work and additive S3/Postgres persistence adapters without overstating deployment readiness.
- Update the tracker so local Phase 5 `#23` reads as in progress and the `#17` / `#23` session pointers move forward to this note.
- Update the pilot architecture note so its current-state and async-job sections match the shipped Phase 5 pilot surface.

## Issues Opened or Updated

- `#17 Maintain roadmap, issue tracker, ADRs, and session notes` - advanced with a narrow post-merge truth sync.
- Local tracker item `#23` - wording updated from untouched next work to in-progress persistence baseline work.

## Docs Touched

- `README.md`
- `docs/issue-tracker.md`
- `docs/pilot-architecture-decision.md`
- `docs/sessions/2026-04-12-issue-17-docs-truth-sync.md`

## Tests and Checks Run

- `python -m ruff check .`
- `python -m pytest -q`

## Outcome

- The README, tracker, and pilot architecture note now match the live repo state after PRs #37, #38, and #39.
- The docs now reflect that pilot auth/request-boundary work exists, additive S3/Postgres persistence work exists, and deployment/cloud rollout still does not.
- The roadmap needed no change because the relevant Phase 5 status rows were already correct on `main`.

## Next-Session Handoff

- Keep any follow-on `#23` work narrow and implementation-focused rather than reopening broad docs cleanup.
- If more docs drift appears after additional persistence slices land, update the relevant session pointers instead of rewriting tracker structure.
