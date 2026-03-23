# Session: Frontend App Shell (Pilot Slice 2)

- Date: 2026-03-22
- Participants: Claude Code (Opus 4.6)
- Related roadmap items: Phase 5 Level 1, #21
- Related ADRs: docs/pilot-architecture-decision.md

## Context

Second coding slice for the pilot web product. The FastAPI wrapper was already in place from slice 1. This session adds a Next.js frontend that lets internal users run workflows through a browser.

## Repo Facts Observed

- FastAPI endpoints return well-structured JSON payloads that map cleanly to frontend display.
- Search response includes a `record` with typed results, taxonomy scores, and failure reasons.
- Answer and research responses include text content and citation arrays.
- All endpoints default to smoke mode, making frontend dev fully offline.

## Decisions Made

- **CORS avoidance via Next.js route handler proxy** — catch-all at `src/app/api/[...path]/route.ts` forwards to FastAPI backend. Backend URL stays server-side only (`BACKEND_URL` env var).
- **Added `/api/health` alias on FastAPI** — allows the proxy to handle health checks uniformly through the `/api/` prefix.
- **Centralized API client** — `src/lib/api-client.ts` provides typed functions so fetch logic is not scattered across components.
- **Tab-based workflow selector** — simple state-driven tabs (Search, Answer, Research) on a single page. Easy to extend with more workflow tabs later.
- **shadcn/ui components manually included** — Button, Input, Card from shadcn/ui New York style. No `npx shadcn init` needed; components are self-contained.
- **@tailwindcss/typography** added for prose styling in research reports.
- **Frontend in `frontend/` subdirectory** — monorepo layout per pilot architecture decision.

## Issues Opened or Updated

- `#21` Frontend app shell — status changed from Next to Done.

## Docs Touched

- `README.md` — Updated current-state section, added feature matrix row, added Frontend section with local dev guide
- `docs/roadmap.md` — Frontend app shell moved to Done
- `docs/issue-tracker.md` — #21 status updated, slice 2 marked done

## Files Created

- `frontend/package.json` — Next.js 15, React 19, Tailwind, shadcn/ui deps
- `frontend/tsconfig.json`, `next.config.ts`, `tailwind.config.ts`, `postcss.config.mjs`
- `frontend/components.json` — shadcn/ui configuration
- `frontend/.env.local.example` — BACKEND_URL template
- `frontend/.gitignore`
- `frontend/src/app/globals.css` — Tailwind + shadcn CSS variables
- `frontend/src/app/layout.tsx` — Root layout with Inter font
- `frontend/src/app/page.tsx` — Main page with tab navigation
- `frontend/src/app/api/[...path]/route.ts` — Backend proxy route handler
- `frontend/src/lib/utils.ts` — cn() utility
- `frontend/src/lib/api-client.ts` — Typed API client
- `frontend/src/components/ui/button.tsx` — shadcn Button
- `frontend/src/components/ui/input.tsx` — shadcn Input
- `frontend/src/components/ui/card.tsx` — shadcn Card
- `frontend/src/components/health-indicator.tsx` — Backend health status dot
- `frontend/src/components/search-panel.tsx` — Search form + results display
- `frontend/src/components/answer-panel.tsx` — Answer form + cited answer display
- `frontend/src/components/research-panel.tsx` — Research form + report display

## Files Modified

- `src/exa_demo/api.py` — Added `/api/health` alias endpoint for proxy compatibility

## Tests and Checks Run

- `npm run build` in `frontend/` — compiled successfully, no type errors
- `python -m ruff check .` — all checks passed
- `python -m pytest -q` — 107 passed

## Outcome

Slice 2 complete. The frontend runs locally via `npm run dev` and can:
- Show backend health status
- Submit search queries and display results with taxonomy scores
- Submit answer questions and display cited answers
- Submit research topics and display reports with sources
- Handle loading and error states on all workflows

All workflows default to smoke mode — no API key or network required for development.

## Next-Session Handoff

Next slice: **Pilot auth + boundary controls** (`#22`)
- Internal-only auth (API key or bearer token)
- Request validation middleware
- Rate limiting
- Per-session budget caps
- Request logging

The proxy route handler at `frontend/src/app/api/[...path]/route.ts` is the natural place to add auth header injection when that slice is built.
