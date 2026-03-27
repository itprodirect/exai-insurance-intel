# Session: Repo AGENTS.md

- Date: 2026-03-27
- Participants: Codex (GPT-5)
- Related scope: repo-native agent execution guidance

## Context

Add a short repo-native `AGENTS.md` that improves agent execution quality without changing product code or widening scope.

## Repo Facts Observed

- No `AGENTS.md` existed anywhere relevant in the repo before this slice.
- `docs/agent-execution-defaults.md` already defined longer-form execution defaults for agents.
- The current repo posture from README and heartbeat is a workflow engine plus thin FastAPI layer and pilot frontend, with Phase 5 Level 1 still focused on bounded pilot hardening.

## Change Made

- Added a root `AGENTS.md` with a short repo purpose summary, current likely focus, “do not touch” boundaries, preferred agent workflow, required output format, and a narrow evidence-backed auth note.

## Validation

- Verified the final `AGENTS.md` sections and wording.
- Regenerated `HEARTBEAT.md` and `heartbeat.json` per normal repo closeout discipline.

## Recommended Next Task

- If later needed, trim overlap between `AGENTS.md` and `docs/agent-execution-defaults.md` once one becomes the clear primary agent guidance surface.
