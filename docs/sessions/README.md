# Session Notes

Session notes are the durable narrative history for this repo.

Use one file per working session in `YYYY-MM-DD-short-name.md` format.

## Required Template

```markdown
# Session: <title>

- Date: YYYY-MM-DD
- Participants: <who worked on it>
- Related roadmap items: <links or issue numbers>
- Related ADRs: <links or none>

## Context

Short statement of why the session happened.

## Repo Facts Observed

- Concrete repo or GitHub facts discovered during the session

## Decisions Made

- Decision and rationale

## Issues Opened or Updated

- Issue number, title, and what changed

## Docs Touched

- Files created or updated

## Tests and Checks Run

- Commands executed and their outcomes

## Outcome

- What was completed this session
- Explicitly note if no feature code was implemented

## Next-Session Handoff

- Recommended next actions
- Known risks, blockers, or assumptions
```

## Rules

- Prefer facts over narrative filler.
- Link roadmap items, ADRs, and issue numbers whenever possible.
- Record why the session made a change, not just what changed.
- If the session is docs-only, say so directly in `Outcome`.
