# Session: Pilot Alignment — Docs, Roadmap, and Architecture Defaults

- Date: 2026-03-22
- Participants: Claude Code (Opus 4.6)
- Related roadmap items: Phase 5 - Pilot Web Product, #19-#23
- Related ADRs: none (this session creates architectural decision docs instead)

## Context

The repo's workflow engine is complete (all CLI commands, evaluation, artifacts, tests, CI). But the docs did not reflect the current state honestly — no mention of what was missing (frontend, API, deployment), and no explicit plan for the pilot web product direction. Future coding agents would have to rediscover and re-debate these decisions each session.

## Repo Facts Observed

- 30 Python modules in `src/exa_demo/`, ~5,500 lines of production code
- 13 test files, ~3,300 lines of test code
- 8 fully implemented CLI commands covering all Exa API endpoints
- Zero frontend code (no JS/TS/React/Next.js)
- Zero HTTP API/web server code
- Zero Docker/Terraform/deployment config
- SQLite is the only persistence layer (local cache)
- No authentication or multi-user support
- All documented capabilities in README are real — no overstated claims found
- Roadmap Phases 0-4 are substantially complete; no Phase 5 existed

## Decisions Made

- **Frontend stack locked:** Next.js 14+ / TypeScript / Tailwind / shadcn/ui / Vercel
- **Backend API locked:** FastAPI thin wrapper over existing workflows
- **Persistence direction locked:** S3 artifacts + Postgres state + SQLite local cache
- **Auth direction locked:** Internal/private first, API key or bearer token
- **Async jobs deferred:** Not required for first pilot unless workflows consistently timeout
- **Monorepo during pilot:** Frontend and backend stay in same repo
- **Agent execution defaults created:** One slice per session, doc updates required, smoke mode non-negotiable

## Issues Opened or Updated

- `#19` Epic: Pilot web product layer (new, Open)
- `#20` Thin FastAPI wrapper (new, Next)
- `#21` Frontend app shell (new, Next)
- `#22` Pilot auth + boundary controls (new, Next)
- `#23` Persistence baseline (new, Next)

Note: GitHub issue numbers are placeholders (TBD) — issues should be created in GitHub to match.

## Docs Touched

- `README.md` — Added "What This Repo Is Today" section with honest current-state framing
- `docs/roadmap.md` — Added Phase 5 with Level 1/2/3 pilot tracks; removed Streamlit from Hold/Explore
- `docs/issue-tracker.md` — Added Phase 5 backlog and "Next Coding Slices" section
- `docs/integration-boundaries.md` — Added "In-Repo vs Later Platform Layers" section with boundary rules
- `docs/pilot-architecture-decision.md` — New: locked architectural defaults for pilot
- `docs/agent-execution-defaults.md` — New: session rules for coding agents

## Tests and Checks Run

- `python -m ruff check .`
- `python -m pytest -q`

## Outcome

Docs-only session. No feature code was implemented. Six documents were created or updated to bring the repo's documentation, roadmap, and architectural decisions into alignment with reality.

## Next-Session Handoff

Top 4 coding slices, in order:

1. **Thin API wrapper** (`#20`): FastAPI app wrapping existing workflow functions. One endpoint per CLI command. JSON in/out. Smoke mode support. Tests against smoke responses.
2. **Frontend app shell** (`#21`): Next.js scaffold with App Router, TypeScript, Tailwind, shadcn/ui. Landing page, search form, results display. Calls API wrapper.
3. **Pilot auth + boundary controls** (`#22`): Internal auth, request validation, rate limiting, budget caps, request logging.
4. **Persistence baseline** (`#23`): S3 artifact storage, Postgres usage tracking, migration from SQLite-only.

Known risks:
- GitHub issues #19-#23 need to be actually created in GitHub (doc references use TBD URLs)
- FastAPI wrapper needs to handle the fact that some workflows (research, comparison) may be slow — monitor whether async/background tasks are needed
- Frontend deploy assumes Vercel access is available
