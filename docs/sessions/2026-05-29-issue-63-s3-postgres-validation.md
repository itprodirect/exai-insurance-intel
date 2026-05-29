# Session: Issue 63 S3/Postgres persistence validation

- Date: 2026-05-29
- Participants: Codex, user
- Related GitHub issue: `#63`
- Related roadmap items: local Phase 5 `#23`
- Related ADRs: none

## Context

Add a bounded, repeatable validation path for the pilot persistence baseline without adding infrastructure, deployment setup, migration redesign, or fake S3/Postgres evidence.

## Repo Facts Observed

- `src/exa_demo/persistence.py` already has local/S3 artifact stores and local/Postgres run repositories.
- `src/exa_demo/api.py` already reports selected persistence backend labels through `/health` and `/api/health`.
- Existing tests cover adapter factories, fake Postgres behavior, S3 location formatting, API health labels, and auth boundaries.
- Prior docs explicitly warned that S3/Postgres-backed runtime behavior had not been validated end to end.

## Changes Made

- Added `scripts/run_pilot_persistence_validation.py`, backed by `exa_demo.pilot_persistence_validation`, for one smoke-mode API workflow with real Postgres run metadata and real S3 artifact storage selected together.
- The validation fails closed unless `PILOT_RUN_STORE=postgres`, `PILOT_ARTIFACT_STORE=s3`, `PILOT_POSTGRES_URL`, `PILOT_S3_BUCKET`, and a validation-scoped `PILOT_S3_PREFIX` are configured.
- The validation checks `/health`, posts one `/api/search` request, reads the matching run through `/api/me/runs`, verifies the persisted `s3://` artifact location/count, and lists the S3 prefix with `boto3`.
- Added focused guardrail tests for the validation config, health label, run matching, and S3 artifact-location checks.
- Updated `.env.example`, local validation docs, integration boundaries, roadmap, and issue tracker wording to document the exact real-service command and avoid overclaiming external evidence.

## Validation Run

- `python -m ruff check src/exa_demo/pilot_persistence_validation.py scripts/run_pilot_persistence_validation.py tests/test_persistence.py` -> passed during implementation.
- `python -m ruff check .` -> passed.
- `python -m pytest -q tests/test_persistence.py tests/test_api.py tests/test_api_auth.py` -> passed (`105 passed`).
- Real S3/Postgres validation command was not run because the environment did not have `PILOT_RUN_STORE`, `PILOT_POSTGRES_URL`, `PILOT_ARTIFACT_STORE`, `PILOT_S3_BUCKET`, `PILOT_S3_PREFIX`, or AWS credential env/profile hints configured.

## Open Issues

- Real external S3/Postgres validation requires actual Postgres, S3, and AWS credentials. They were unavailable in this session, so no external pass is claimed.
- Local Phase 5 `#23` remains in progress until real S3/Postgres execution evidence is produced or the pilot persistence baseline is otherwise closed.

## Decisions Proposed

- Keep the validation command smoke-mode for Exa traffic but real for S3/Postgres persistence.
- Keep the command out of CI by default because it requires external services and credentials.
- Use `live-validation-artifacts/` for local JSON evidence output so runtime evidence is not committed.

## Next Thin Slice

- Run `python scripts/run_pilot_persistence_validation.py --output live-validation-artifacts/pilot-s3-postgres-validation.json` in an environment with the required external Postgres and S3 credentials, then record the actual evidence if it passes.
