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
| Thin FastAPI wrapper (next) | Thin adapter over existing workflows; belongs with the code it wraps |
| Frontend app (next) | Product UI; lives in-repo as `frontend/` or similar until scale demands separation |

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
- Keep the API wrapper thin — it should delegate to existing workflow functions, not duplicate logic.
- Frontend and backend can share a monorepo during pilot. Separation is a Level 3 concern.
- Auth should start as simple middleware in the API layer, not as a separate service.
