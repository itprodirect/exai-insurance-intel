# Agent Execution Defaults

These rules define how coding agents (Claude Code, Codex, etc.) should work on this repo. The goal is to reduce ambiguity so agents can execute focused slices without repeatedly debating basic decisions.

## Session Rules

1. **One focused slice per session.** Each session should target one item from the issue tracker. Do not combine unrelated work.
2. **Read before writing.** Read the relevant existing code, tests, and docs before making changes. Do not propose changes to code you have not read.
3. **Preserve existing contracts.** Existing CLI commands, artifact shapes, and test expectations are stable. New work should be additive, not breaking.
4. **Smoke mode works offline.** Any new code that touches the Exa API must support smoke mode (mocked responses, no network). This is non-negotiable.

## Validation Expectations

Before considering a session complete:

- `python -m ruff check .` passes
- `python -m pytest -q` passes
- Any new code has tests (unit or integration)
- If a new CLI command or API endpoint was added, it works in smoke mode
- Any new single-record route returning user-owned data enforces explicit owner-or-ops access at the route boundary and includes tests for owner read, non-owner denial, and ops read when allowed

## Doc Update Rules

After code changes, update docs in the same session:

- **README.md**: Update the feature matrix if a new capability was added. Do not claim capabilities that are not yet implemented.
- **docs/roadmap.md**: Move completed items to `Done`. Do not change scope of other items.
- **docs/issue-tracker.md**: Update status and session log reference for the issue you worked on.
- **Session log**: Write a session note in `docs/sessions/` capturing what changed and what is next.

## How to Avoid Overstating Production Readiness

- Do not describe anything as "production-ready" unless it has: tests, error handling, observability hooks, and has been validated in live mode.
- Use "implemented" or "functional" for code that works in smoke and live modes.
- Use "scaffolded" or "stubbed" for code that exists but is not yet tested or connected.
- If a feature only works in smoke mode, say so explicitly.

## Architectural Defaults

When making implementation decisions during a session, use these defaults unless the task explicitly overrides them:

| Area | Default | Reference |
| --- | --- | --- |
| Frontend stack | Next.js + TypeScript + Tailwind + shadcn/ui | [pilot-architecture-decision.md](./pilot-architecture-decision.md) |
| API layer | FastAPI, thin wrapper | [pilot-architecture-decision.md](./pilot-architecture-decision.md) |
| Deploy target | Vercel (frontend), AWS-compatible (backend) | [pilot-architecture-decision.md](./pilot-architecture-decision.md) |
| Persistence | S3 artifacts + Postgres state + SQLite local cache | [pilot-architecture-decision.md](./pilot-architecture-decision.md) |
| Auth | Internal/private, API key or bearer token | [pilot-architecture-decision.md](./pilot-architecture-decision.md) |
| Execution modes | smoke / live / auto (smoke is default) | [integration-boundaries.md](./integration-boundaries.md) |

## Next Coding Slices

See [issue-tracker.md](./issue-tracker.md) for the current sequenced backlog. The immediate next slices are:

1. Thin FastAPI wrapper over existing workflows
2. Frontend app shell (Next.js + Tailwind + shadcn/ui)
3. Pilot auth + request/budget boundary controls
4. Persistence/state baseline (S3 + Postgres)
