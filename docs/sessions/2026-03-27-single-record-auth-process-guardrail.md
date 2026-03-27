# Session: Single-Record Auth Process Guardrail

- Date: 2026-03-27
- Participants: Codex (GPT-5)
- Related scope: repo-process safeguard for single-record auth reviews

## Context

Add one minimal repo-process guardrail to prevent future single-record auth regressions after an evidence-backed audit found no remaining gap in the current run/job read boundary.

## Repo Facts Observed

- No `AGENTS.md` file exists in this repo.
- No PR template exists under `.github/`.
- `.agents/skills/tier-a-review/SKILL.md` exists locally, but `.agents/` is gitignored and not suitable for this branch closeout.
- The smallest existing tracked review/process surface is `docs/agent-execution-defaults.md`.

## Change Made

- Added one short review rule to `docs/agent-execution-defaults.md` requiring explicit owner-or-ops enforcement and three cross-user tests for any new single-record route returning user-owned data.

## Exact Guidance Added

- For any new single-record route returning user-owned data, require explicit owner-or-ops enforcement at the route boundary plus tests for owner read, non-owner denial, and ops read when allowed.

## Validation

- Verified the rule was added in `docs/agent-execution-defaults.md`.
- Regenerated `HEARTBEAT.md` and `heartbeat.json` per current repo closeout discipline.

## Recommended Next Task

- When the next user-owned single-record route is introduced, apply this checklist rule in review and require the three cross-user tests in the same slice.
