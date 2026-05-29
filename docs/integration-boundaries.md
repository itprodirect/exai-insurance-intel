# Integration Boundaries

This repo is designed to stay safe-by-default while still supporting deliberate live validation.

## Execution Modes

- `smoke`: no network, no Exa billing, mocked responses only
- `live`: real Exa API calls, requires `EXA_API_KEY`, can incur billing
- `auto`: resolves to `live` only when `EXA_API_KEY` is configured; otherwise falls back to `smoke`

## Default Delivery Rule

- Use `smoke` for development, CI, docs walkthroughs, and regression checks.
- Use `live` only for explicit manual validation when you want to inspect real API behavior.
- Keep human review in the loop for any operational interpretation of results, even in `live`.

## Exa 2026 Request Boundary

- User-facing `research` remains a shipped workflow name in the CLI, API, and frontend, but the Exa transport is `/search` with `type="deep-reasoning"`.
- Do not describe or implement a live Exa `/research` endpoint for this repo unless the vendor surface changes and is explicitly revalidated.
- Freshness controls should be expressed through `contents.maxAgeHours`, including `--freshness always-live` or `--max-age-hours 0` for always-live behavior.
- Outgoing request payloads must not emit deprecated `livecrawl`, `highlightsPerUrl`, `numSentences`, `startCrawlDate`, or `endCrawlDate` fields.
- Cost estimates use centralized, overrideable pricing assumptions and should not be described as exact live billing unless live Exa `costDollars` fields validate the run. Do not claim grounding quality, S3, Postgres, or deployed validation until those paths actually run.

## Current Locally Validated Path (2026-04-12)

- Rebuilt an isolated virtual environment and installed with `python -m pip install --no-user -e '.[dev,api]'`
- Passed `python -m pytest -q`, `python -m ruff check .`, and `python scripts/run_live_validation.py --mode smoke`
- Booted the FastAPI app locally and verified `/health` and `/docs`
- Booted the Next.js frontend locally and verified Search, Answer, Research, and My Work against the local backend
- Did **not** revalidate `live` mode, S3 artifact storage, or Postgres-backed usage/run persistence

## Bounded S3/Postgres Persistence Validation

Issue `#63` adds a narrow real-service validation command for the pilot persistence baseline:

```powershell
python scripts/run_pilot_persistence_validation.py --output live-validation-artifacts/pilot-s3-postgres-validation.json
```

This path is deliberately smoke-mode for Exa traffic, but real for persistence. It must run with `PILOT_RUN_STORE=postgres`, `PILOT_POSTGRES_URL`, `PILOT_ARTIFACT_STORE=s3`, `PILOT_S3_BUCKET`, and a validation-scoped `PILOT_S3_PREFIX`. AWS credentials must be available to `boto3` with upload/list access to the selected prefix. If API auth is enabled, `PILOT_VALIDATION_API_KEY` must contain a valid pilot API key.

The command fails closed unless `/health` reports `run_store=postgres` and `artifact_store=s3`, one `/api/search` smoke request completes, the matching run is visible through `/api/me/runs`, the persisted `artifact_location` is the selected `s3://` prefix, and the S3 prefix lists at least the persisted artifact count.

This command does not create infrastructure, deploy the app, redesign migrations, or prove live Exa behavior. Do not claim S3/Postgres validation passed unless this command exits `0` against real external Postgres and S3 services.

## Bounded Live Grounding Validation (2026-05-27)

After replacing the placeholder Exa API key, a narrow live CLI rerun validated only `research` and `structured-search` grounding behavior:

- Live `research` completed against `https://api.exa.ai/search` with `request_id=7f2b06e5b419f4ca182d1144c0c9e4d9`, `actual_cost_usd=0.015`, and 5 results, but the response did not include `output.content` or `output.grounding`.
- Live `structured-search` completed with `request_id=c4e750dd01ad3bb1ce78621663609d59`, `actual_cost_usd=0.012`, `output.content`, `output.grounding`, and `grounding_count=26`.
- The structured-search `report.md` rendered `Grounding / Source Review`, confirming the current Markdown path surfaces preserved grounding metadata.

This was not a frontend, S3, Postgres, deployment, monitoring, or broad production validation.

## Artifact Expectations

- Smoke runs preserve the same artifact shape as live runs whenever possible.
- Workflow-specific payloads remain additive. Existing JSON and JSONL contracts should not be rewritten just because a new export is added.
- Every run records runtime execution metadata in `config.json`, `summary.json`, and `manifest.json` so reviewers can distinguish smoke artifacts from live artifacts.
- Manual live validation should assert the expected artifact contract for each workflow before the run is treated as successful.
- Contract checks should confirm the presence of the workflow-specific artifact file plus the core summary output for that run.
- Single-workflow live validations should also assert that the emitted JSON payload includes a non-empty `request_id`.

## CI Boundary

- CI should stay smoke-only by default.
- CI is allowed to run lint, pytest, and the notebook smoke runner.
- Live API validation should remain an explicit manual workflow until its scope, spend guardrails, secrets handling, and artifact assertions are documented more tightly.
- The manual live-validation path is [`.github/workflows/live-validation.yml`](../.github/workflows/live-validation.yml), backed by [`scripts/run_live_validation.py`](../scripts/run_live_validation.py).
- The runner writes a `validation_summary.json` file plus the underlying workflow artifacts for review; these outputs are runtime artifacts and should not be committed.
- The manual workflow should fail closed on a missing `EXA_API_KEY` in live mode and should keep comparison validation opt-in.

## Cost and Safety Boundary

- Cached reruns should not re-bill.
- Live validation should stay bounded to small, intentional runs.
- Comparison validation should stay opt-in because it performs multiple real search calls.
- Public/professional info only.
- No address hunting, contact harvesting, or operational use without human review.

## In-Repo vs Later Platform Layers

This section clarifies what belongs in the repo now versus what should be deferred to platform or infrastructure layers.

### In-repo now (owns the code)

| Component | Rationale |
| --- | --- |
| Workflow engine (`src/exa_demo/`) | Core business logic; tested; stable |
| CLI + notebook interfaces | Existing user surfaces |
| SQLite cache + budget ledger | Local dev and smoke mode persistence |
| Benchmark fixtures and evaluation | Domain-specific; tightly coupled to workflows |
| Thin FastAPI wrapper | Thin adapter over existing workflows; belongs with the code it wraps |
| Frontend app | Product UI; lives in-repo as `frontend/` until scale demands separation |

### Deferred to platform / infra layers

| Component | Rationale |
| --- | --- |
| Container orchestration (ECS/K8s) | Deploy-time concern; not needed for pilot |
| Infrastructure as code (Terraform/CDK) | Separate repo or separate directory once pilot is validated |
| Secret management (AWS Secrets Manager, Vault) | Environment-level concern; use env vars for pilot |
| CDN / edge config | Vercel handles this for frontend; backend can add later |
| Log aggregation / APM (Datadog, etc.) | Platform-level; structured logging in-repo is sufficient for pilot |
| CI/CD pipeline for production deploy | GitHub Actions handles smoke CI; production deploy pipeline is a Level 2+ concern |

### Boundary rules

- Do not add infrastructure-as-code to the repo until the pilot architecture is validated with real users.
- Keep the API wrapper thin - it should delegate to existing workflow functions, not duplicate logic.
- Frontend and backend can share a monorepo during pilot. Separation is a Level 3 concern.
- Auth should start as simple middleware in the API layer, not as a separate service.
- Do not blur additive S3/Postgres code paths with the current validated local smoke path unless they have been explicitly revalidated end to end.
