# Pilot Architecture Decision

Locked: 2026-03-22

This document records the near-term architectural defaults for the pilot web product layer. These decisions are intentionally simple and designed to unblock agent execution on the next coding slices. They can be revisited once the pilot is validated with real users.

## Current State

The repo is a fully implemented **backend workflow engine** with:
- 8 CLI commands covering all Exa API endpoints
- SQLite caching with budget enforcement
- Evaluation taxonomy and benchmark suites
- Artifact export system
- Comprehensive test suite

There is no web frontend, no HTTP API layer, no container deployment, and no production database.

## Target: Private Internal Pilot

A working web product that internal users can use to run insurance intelligence workflows through a browser. Not a public product. Not a platform. A controlled pilot.

## Locked Decisions

### Frontend Stack

| Decision | Choice | Rationale |
| --- | --- | --- |
| Framework | Next.js 14+ with App Router | Industry standard; good DX; SSR when needed |
| Language | TypeScript (strict) | Type safety across the stack |
| Styling | Tailwind CSS | Utility-first; fast iteration |
| Component library | shadcn/ui | Composable; no vendor lock-in; Tailwind-native |
| Deploy target | Vercel | Zero-config for Next.js; handles CDN/edge |
| Repo location | `frontend/` directory in monorepo | Keep together during pilot; separate later if needed |

### Backend API Layer

| Decision | Choice | Rationale |
| --- | --- | --- |
| Framework | FastAPI | Lightweight; async-capable; good OpenAPI generation |
| Pattern | Thin wrapper over existing workflow functions | No logic duplication; one endpoint per CLI command |
| Response format | JSON matching existing artifact schemas | Frontend consumes the same shapes the CLI produces |
| Smoke mode | Supported via query param or config | Frontend dev works without Exa API key |
| Deploy direction | AWS-compatible service path (ECS/Lambda) | Standard; team-familiar; can start with single instance |
| Repo location | `api/` directory or extend `src/exa_demo/` | Keep close to workflow code it wraps |

### Persistence

| Decision | Choice | Rationale |
| --- | --- | --- |
| Artifact storage | S3 (or S3-compatible) | Durable; cheap; existing artifact shapes map directly |
| Relational state | Postgres | Usage tracking, user state, run metadata |
| Local dev cache | Keep existing SQLite | Works; no reason to change for local/smoke mode |
| Migration approach | Additive — S3 and Postgres supplement SQLite, not replace it | SQLite stays for CLI/notebook; pilot adds cloud persistence |

### Auth and Controls

| Decision | Choice | Rationale |
| --- | --- | --- |
| Auth model | Internal/private first | No public signup; controlled access only |
| Auth mechanism | API key or simple bearer token | Simplest thing that works for internal pilot |
| Request validation | FastAPI request models with Pydantic | Already natural in FastAPI |
| Rate limiting | Middleware-level, per-user | Prevents runaway usage |
| Budget guardrails | Extend existing cost_model.py to API layer | Reuse what exists |
| Request logging | Structured JSON logs per request | Minimum for audit and debugging |

### Observability Minimums

| Decision | Choice | Rationale |
| --- | --- | --- |
| Logging | Structured JSON to stdout | Collectable by any log aggregator later |
| Error tracking | Log errors with request context; no external service yet | Add Sentry/similar at Level 2 |
| Cost tracking | Existing budget ledger extended to API requests | Already implemented for CLI |
| Health check | `/health` endpoint returning service status | Standard practice |

### Async Jobs

Long-running async jobs are **not required for the first pilot** unless testing reveals that research or comparison workflows consistently exceed reasonable HTTP timeout thresholds. If needed, the simplest path is a background task queue (e.g., FastAPI BackgroundTasks or a simple Redis/Celery setup), not a full job orchestration system.

## What This Does NOT Decide

- Production infrastructure (Terraform, CDK, CI/CD pipelines)
- Multi-tenant architecture
- Public-facing auth (OAuth, SSO)
- Horizontal scaling strategy
- Frontend/backend repo separation
- Pricing or billing

These are Level 2+ concerns and should not block pilot execution.
