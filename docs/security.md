# Security Posture

This document describes the security controls in place, what's enforced automatically, and what's deferred to later phases.

## CI Security Pipeline

The `ci.yml` workflow runs two parallel jobs on every push and PR:

### `lint-and-test`
- **Ruff** linting (style + error detection)
- **pytest** full test suite
- **Notebook smoke execution** (no-network mode)
- **Bounded smoke validation**

### `security`
- **pip-audit** — Checks installed dependencies against the Python Advisory Database (PyPA) for known CVEs. Runs with `--strict` (non-zero exit on any finding) and `--skip-editable` (ignores local dev packages).
- **bandit** — Static Application Security Testing (SAST) for Python. Scans `src/` for common vulnerability patterns (hardcoded passwords, unsafe deserialization, shell injection, etc.).
- **detect-secrets** — Scans all tracked files for potential leaked secrets (API keys, tokens, passwords). Excludes notebooks and experiment artifacts.

### Global bandit skips

| Rule | Reason |
|------|--------|
| B101 | `assert` used in tests — not a security concern |
| B311 | `random.uniform` used for backoff jitter, not cryptographic purposes |
| B608 | All SQL in this codebase uses parameterized queries; f-strings build column/placeholder lists from internal schema constants, not user input |

## Pre-commit Hooks

`.pre-commit-config.yaml` enforces three hooks locally before code reaches CI:

| Hook | Scope | Purpose |
|------|-------|---------|
| **ruff** | `src/`, `scripts/`, `tests/` | Lint and style enforcement |
| **bandit** | `src/` | SAST on changed files |
| **detect-secrets** | All files (excl. notebooks, experiments) | Prevent secret leaks at commit time |

Install with: `pre-commit install`

## Runtime Security Controls

### PII Redaction (`safety.py`)
- Regex-based redaction of emails, phone numbers, and street addresses
- Applied to all Exa API responses before caching or display
- Enabled by default (`redact_emails_phones: True`)
- Operates on `text`, `summary`, `title`, `author`, `highlights`, and `answer` fields

### API Authentication (`api_auth.py`)
- Bearer token validation (multi-user or single shared key)
- Sliding-window rate limiting (default 60 req/min, returns 429). Multi-user mode isolates buckets per authenticated user; single-key and no-auth modes fall back to per-IP limiting.
- Ops user allowlist for admin endpoints
- Live mode gated behind `PILOT_ALLOW_LIVE_MODE=1`

### Input Validation
- Query length bounded (`PILOT_MAX_QUERY_LENGTH`, default 1000 chars), including saved-query writes
- Result count clamped (`PILOT_MAX_RESULTS`, default 25)
- Saved-query workflows limited to the currently shipped pilot surfaces (`search`, `answer`, `research`)
- Pydantic model validation on all API request bodies
- Request ID tracking via `X-Request-ID` header

### Resilience (`resilience.py`)
- Circuit breaker pattern for Exa API calls
- Exponential backoff with jitter on transient failures (429, 5xx, timeouts)
- Fast-fail on non-transient errors (4xx, RuntimeError)
- Thread-safe state machine (CLOSED / OPEN / HALF_OPEN)

### Execution Modes
- **smoke** (default): No network calls, no billing, mocked responses
- **live** (manual): Real Exa API, requires `EXA_API_KEY`, incurs billing
- **auto**: Falls back to smoke if no API key present

### Budget Controls
- Default budget cap: $7.50 USD per run
- SQLite cache prevents re-billing on repeated queries (30-day TTL)
- Cost tracking in experiment artifacts

## What's NOT In Scope (Deferred)

These are acknowledged gaps, deferred to later phases per the roadmap:

| Area | Status | Notes |
|------|--------|-------|
| Distributed rate limiting | Deferred | Current in-memory limiter is per-process; adequate for pilot |
| ML-based PII detection | Deferred | Regex covers emails/phones/addresses; no SSN/credit card patterns yet |
| CORS / CSRF protection | Deferred | Depends on frontend/proxy deployment topology |
| Request body size limits | Deferred | Low risk at current pilot scale |
| Infrastructure-as-code scanning | Deferred | No IaC exists yet (Phase 5 Level 3) |
| Dependency auto-update (Dependabot/Renovate) | Deferred | pip-audit catches known CVEs; auto-PRs can be added later |
| SBOM generation | Deferred | Can be added to CI when compliance requires it |

## Integration Boundaries

See [integration-boundaries.md](./integration-boundaries.md) for the execution mode contracts, artifact formats, and cost/safety guardrails that govern how this repo interacts with external systems.
