# Local Validation Runbook

This runbook captures the repo's **current validated local state** as rechecked on **2026-04-12**.

## Validated Today

- Rebuilt and activated an isolated Python virtual environment
- Installed the package and extras with `python -m pip install --no-user -e '.[dev,api]'`
- Passed `python -m pytest -q`
- Passed `python -m ruff check .`
- Passed `python scripts/run_live_validation.py --mode smoke`
- Booted the FastAPI app locally with `uvicorn exa_demo.api:app --reload`
- Verified `http://127.0.0.1:8000/health`
- Verified `http://127.0.0.1:8000/docs`
- Booted the frontend locally from `frontend/` with `npm install` and `npm run dev`
- Verified frontend-to-backend connectivity at `http://localhost:3000`
- Verified Search, Answer, Research, and My Work through the UI

## Not Validated Today

- Live Exa mode (`--mode live`)
- Real Exa API billing or live result quality
- Real S3 artifact storage unless the bounded S3/Postgres command below is run
- Real Postgres-backed usage or run persistence unless the bounded S3/Postgres command below is run
- Production deployment, production readiness, or infrastructure rollout

## Bounded S3/Postgres Pilot Persistence Validation

This command is the repeatable issue `#63` path for real pilot persistence validation. It is intentionally not local SQLite evidence and not mock/fake S3 evidence.

It runs one smoke-mode `/api/search` request through the FastAPI app, checks `/health` reports `run_store=postgres` and `artifact_store=s3`, reads the persisted run back through `/api/me/runs`, and lists the persisted S3 prefix with `boto3`. It exits without claiming success if the selected backends, required env vars, credentials, or services are missing.

Required install:

```powershell
python -m pip install --no-user -e '.[pilot]'
```

Required services and credentials:

- A reachable Postgres database in `PILOT_POSTGRES_URL`. The existing adapter creates the `runs` and `saved_queries` tables if they do not exist.
- An existing S3 bucket in `PILOT_S3_BUCKET`.
- AWS credentials available to `boto3` through the normal AWS chain, with permission to upload and list objects under `PILOT_S3_PREFIX`.
- Optional API bearer auth. If auth is enabled, set `PILOT_VALIDATION_API_KEY` to a valid pilot user's API key; in single-key mode `PILOT_API_KEY` is also accepted by the script.

Required environment variables:

```powershell
$env:PILOT_RUN_STORE = "postgres"
$env:PILOT_POSTGRES_URL = "postgresql://USER:PASSWORD@HOST:5432/DBNAME"
$env:PILOT_ARTIFACT_STORE = "s3"
$env:PILOT_S3_BUCKET = "your-existing-validation-bucket"
$env:PILOT_S3_PREFIX = "validation/pilot-persistence/"
```

Optional auth header source:

```powershell
$env:PILOT_VALIDATION_API_KEY = "pilot-user-api-key"
```

Run:

```powershell
python scripts/run_pilot_persistence_validation.py --output live-validation-artifacts/pilot-s3-postgres-validation.json
```

Expected success evidence:

- JSON output with `status` set to `passed`
- `health.run_store` is `postgres`
- `health.artifact_store` is `s3`
- `postgres_evidence.source` is `/api/me/runs`
- `artifact_location` starts with `s3://<PILOT_S3_BUCKET>/<PILOT_S3_PREFIX>`
- `artifact_count` is at least `1`
- `s3_object_count` is at least the persisted `artifact_count`

Exit codes:

- `0`: real S3/Postgres validation passed
- `1`: the command ran but validation failed
- `2`: required external configuration was missing or still local-only

Do not commit the JSON evidence file or generated runtime artifacts. `live-validation-artifacts/` and `experiments/` are local runtime output paths.

## Reproduce The Local Smoke Path

1. Create and activate the virtual environment.

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Git Bash:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

2. Install the package, dev tooling, and FastAPI dependencies.

```powershell
python -m pip install --upgrade pip
python -m pip install --no-user -e '.[dev,api]'
```

3. Copy the backend env file.

PowerShell:

```powershell
Copy-Item .env.example .env
```

Git Bash:

```bash
cp .env.example .env
```

4. Run the validated Python checks.

```powershell
python -m pytest -q
python -m ruff check .
python scripts/run_live_validation.py --mode smoke
```

5. Start the backend.

```powershell
uvicorn exa_demo.api:app --reload
```

Check:
- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

The health response should include `status`, `run_store`, and `artifact_store` so local checks can confirm which persistence backends the API process selected.

6. Start the frontend in a second terminal.

```powershell
cd frontend
npm install
```

Copy the frontend env file.

PowerShell:

```powershell
Copy-Item .env.local.example .env.local
```

Git Bash:

```bash
cp .env.local.example .env.local
```

Start the frontend:

```powershell
npm run dev
```

Open `http://localhost:3000`.

7. Recheck the validated UI flow.

- Run Search
- Run Answer
- Run Research
- Confirm My Work shows the new runs

## Boundary Notes

- The validated path above is still **local + smoke/mock only**.
- Do not treat this local UI smoke runbook as evidence that live Exa mode was revalidated.
- A separate bounded live CLI grounding rerun on 2026-05-27 validated only `research` and `structured-search`; see [2026-05-27-live-grounding-validation.md](sessions/2026-05-27-live-grounding-validation.md).
- Do not treat the S3/Postgres command above as evidence unless it exits `0` against real external services and its JSON evidence is reviewed.
- Treat deployment and production hardening as future work, not current state.

## Troubleshooting

If `pip` appears to install outside `.venv`, reactivate the virtual environment and use `python -m pip` instead of bare `pip`.

Useful checks:

```powershell
python -c "import sys; print(sys.executable)"
python -m pip --version
```

Both should point at the active `.venv` before you install dependencies.
