# Session: Pull Request Template

- Date: 2026-03-27
- Participants: Codex (GPT-5)
- Related scope: repo-native PR review guidance

## Context

Add a tracked `.github/PULL_REQUEST_TEMPLATE.md` so thin slices are reviewed consistently without widening scope or changing product behavior.

## Repo Facts Observed

- `.github/` already exists and currently contains workflow files only.
- No PR template existed anywhere relevant in the repo.
- Root `AGENTS.md` already covers repo purpose, bounded workflow expectations, and narrow evidence-backed auth work, so the PR template should stay checklist-style and avoid duplicating that guidance.

## Change Made

- Added `.github/PULL_REQUEST_TEMPLATE.md` with concise sections for summary, scope boundary, validation, risks/follow-ups, and a conditional single-record auth checklist.

## Validation

- Verified the final template sections and checklist wording.
- Regenerated `HEARTBEAT.md` and `heartbeat.json` per normal repo closeout discipline.

## Recommended Next Task

- If contributor workflow expands later, align the PR template and `AGENTS.md` periodically so they stay complementary rather than drifting.
