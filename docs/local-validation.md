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
- S3 artifact storage
- Postgres-backed usage or run persistence
- Production deployment, production readiness, or infrastructure rollout

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
- Do not treat the current docs as evidence that live Exa mode was revalidated.
- Do not treat the current docs as evidence that S3 or Postgres-backed persistence was exercised end to end.
- Treat deployment and production hardening as future work, not current state.

## Troubleshooting

If `pip` appears to install outside `.venv`, reactivate the virtual environment and use `python -m pip` instead of bare `pip`.

Useful checks:

```powershell
python -c "import sys; print(sys.executable)"
python -m pip --version
```

Both should point at the active `.venv` before you install dependencies.
