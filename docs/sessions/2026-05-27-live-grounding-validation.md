# Session: Live Exa grounding validation attempt

- Date: 2026-05-27
- Scope: bounded live validation attempt for `research` and `structured-search` grounding normalization

## Goal

Validate real Exa `output.grounding` variants against the current artifact normalizer without widening product, UI, deployment, persistence, monitor, MCP, or agent surfaces.

## Pre-live checks

- Branch: `codex/live-grounding-validation`
- Clean status before validation: yes
- Based on latest `origin/main`: yes, `git rev-list --left-right --count origin/main...HEAD` returned `0 0` after `git fetch origin main`
- `EXA_API_KEY`: present through the CLI dotenv loading path

## Commands Attempted

Baseline smoke and tests:

```powershell
python -m ruff check .
python -m pytest -q
python scripts/run_live_validation.py --mode smoke
```

Live research attempt:

```powershell
python -m exa_demo research "Summarize recent Florida CAT insurance market signals for claims leaders." --mode live --run-id grounding-live-research-20260527T1930Z --artifact-dir live-validation-artifacts --sqlite-path live-validation-artifacts\grounding-live-20260527T1930Z.sqlite --budget-cap-usd 0.03 --json
```

Live structured-search attempt:

```powershell
python -m exa_demo structured-search "Florida independent adjuster catastrophe claims firms" --schema-file assets\live_validation_schema.json --mode live --run-id grounding-live-structured-20260527T1930Z --artifact-dir live-validation-artifacts --sqlite-path live-validation-artifacts\grounding-live-20260527T1930Z.sqlite --num-results 1 --budget-cap-usd 0.02 --json
```

## Live Result

Both live commands reached `https://api.exa.ai/search` and failed with:

```text
401 Client Error: Unauthorized for url: https://api.exa.ai/search
```

No live `research.json`, `structured_output.json`, `research.md`, or `report.md` artifacts were written for the attempted live run ids.

## Artifact Inspection

Because Exa returned `401 Unauthorized` before a response body was available, there were no real live `output.grounding` shapes to inspect.

The required smoke baseline artifacts from `python scripts/run_live_validation.py --mode smoke` were inspected as a contract check:

- `live-validation-artifacts/live-validation-20260527T192831Z-research/research.json`
- `live-validation-artifacts/live-validation-20260527T192831Z-research/research.md`
- `live-validation-artifacts/live-validation-20260527T192831Z-research/report.md`
- `live-validation-artifacts/live-validation-20260527T192831Z-structured/structured_output.json`
- `live-validation-artifacts/live-validation-20260527T192831Z-structured/report.md`

Smoke artifact observations:

- Research artifact has `request_id=smoke-2a58bf88`, `output_content` as a string, `grounding` as an object array, `grounding_count=5`, `actual_cost_usd=0.0`, and `response.costDollars.total=0.0`.
- Structured-search artifact has `request_id=smoke-1e81f24e`, `output_content` as an object, `grounding` as an object array, `grounding_count=5`, `actual_cost_usd=0.0`, and `response.costDollars.total=0.0`.
- `research.md`, research `report.md`, and structured-search `report.md` all render `## Grounding / Source Review`.

## Real Grounding Shape Observations

No real Exa `output.grounding` shape was observed in this session. The live blocker is authorization, not a normalizer mismatch.

## Follow-Up

Refresh or replace the configured Exa API key, then rerun only the two bounded live commands above. If real responses expose a normalizer mismatch, keep the fix in `src/exa_demo/workflows.py` with focused tests in `tests/test_workflow_builders.py`.
