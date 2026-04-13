# Session: Local smoke validation doc sync

Date: 2026-04-12
Type: docs-only
Related issue: #17

## Goal

Update the docs so they reflect the repo's current validated local smoke path without overstating live-mode, persistence, or production status.

## What Changed

- Updated `README.md` to:
  - describe the repo as a Python package/CLI plus FastAPI backend and Next.js frontend
  - add a dated current local status section
  - replace stale local install commands with the validated `python -m pip install --no-user -e '.[dev,api]'` flow
  - make setup and env-copy steps friendlier to both PowerShell and Git Bash
  - point contributors at the exact local smoke validation path and URLs
  - distinguish validated smoke checks from unvalidated live-mode and S3/Postgres-backed paths
- Added `docs/local-validation.md` as a focused runbook for reproducing the validated local smoke path.
- Updated `docs/demo-gallery.md`, `docs/integration-boundaries.md`, `docs/pilot-architecture-decision.md`, and `docs/roadmap.md` so shipped web surfaces are no longer described as "next" and persistence target-state language is clearly separated from what has actually been locally validated.

## Validation

- Docs review only
- No application code changes

## Outcome

The top-level docs now tell a new contributor how to reproduce the currently validated local smoke path and explicitly call out what remains unvalidated.
