# AGENTS

## Repo purpose

`exai-insurance-intel` is an Exa-powered insurance intelligence repo with a Python workflow engine, a thin FastAPI layer, and a pilot Next.js UI for CAT-loss, claims, expert, contractor, and market research workflows.

## Current likely focus

The current repo focus is the Phase 5 Level 1 pilot slice: keep the shipped workflow/API/frontend surface stable while tightening auth/request boundaries, persistence posture, and execution discipline in small validated steps.

## Do not touch without explicit instruction

- auth redesign or widening access scope
- persistence redesign or storage migrations
- deployment / infra setup
- broad docs rewrites that go beyond the current slice
- unrelated product routes, UI flows, or workflow behavior

## Preferred workflow for agents

1. Inspect before editing: read the relevant code, tests, and docs first.
2. Work one thin slice at a time: do not mix unrelated fixes.
3. Preserve behavior where possible: prefer additive or narrow changes over redesigns.
4. Validate the narrowest affected surface first, then stop unless broader checks are clearly needed.
5. Keep doc updates minimal: session log, memory entry, and heartbeat regeneration when this repo's closeout discipline calls for it.

## Required output format

- summary
- changed files
- validation
- unresolved issues
- recommended next task

## Auth note

Repo-level auth or access-boundary changes must stay narrow, evidence-backed, and tied to explicit route/test inspection before any edit is made.
