# Session: Live Exa grounding validation

- Date: 2026-05-27
- Scope: bounded live validation for `research` and `structured-search` grounding normalization
- Related issues: [#51](https://github.com/itprodirect/exai-insurance-intel/issues/51), [#56](https://github.com/itprodirect/exai-insurance-intel/issues/56)

## Goal

Validate real Exa `output.grounding` variants against the current artifact normalizer without widening product, UI, deployment, persistence, monitor, MCP, or agent surfaces.

## Pre-live checks

- Branch: `codex/live-grounding-validation`
- Clean status before validation: yes
- Based on latest `origin/main`: yes, `git rev-list --left-right --count origin/main...HEAD` returned `0 0` after `git fetch origin main`
- `EXA_API_KEY`: present through the CLI dotenv loading path
- GitHub issue recheck during docs sync: `#51` was closed at `2026-05-27T19:50:56Z`; `#56` was closed at `2026-05-27T20:02:35Z`

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

## Initial Live Result

Both live commands reached `https://api.exa.ai/search` and failed with:

```text
401 Client Error: Unauthorized for url: https://api.exa.ai/search
```

No live `research.json`, `structured_output.json`, `research.md`, or `report.md` artifacts were written for the attempted live run ids.

## Successful Live Rerun After API Key Refresh

After the placeholder Exa API key was replaced, the bounded live rerun completed for the two targeted workflows:

```powershell
python -m exa_demo research "Summarize recent Florida CAT insurance market signals for claims leaders." --mode live --run-id grounding-live-20260527T155447-research --artifact-dir live-validation-artifacts --sqlite-path live-validation-artifacts\grounding-live-20260527T155447.sqlite --budget-cap-usd 0.03 --json
python -m exa_demo structured-search "Florida independent adjuster catastrophe claims firms" --schema-file assets\live_validation_schema.json --mode live --run-id grounding-live-20260527T155447-structured --artifact-dir live-validation-artifacts --sqlite-path live-validation-artifacts\grounding-live-20260527T155447.sqlite --num-results 1 --budget-cap-usd 0.02 --json
```

Observed live artifacts:

- `live-validation-artifacts/grounding-live-20260527T155447-research/research.json`
- `live-validation-artifacts/grounding-live-20260527T155447-research/research.md`
- `live-validation-artifacts/grounding-live-20260527T155447-research/report.md`
- `live-validation-artifacts/grounding-live-20260527T155447-structured/structured_output.json`
- `live-validation-artifacts/grounding-live-20260527T155447-structured/report.md`

Live research outcome:

- `request_id=7f2b06e5b419f4ca182d1144c0c9e4d9`
- `actual_cost_usd=0.015`
- Response included `results` with 5 items.
- Response did not include `output.content` or `output.grounding`, so `grounding_count=0` and no live grounding shape was available from the research response.

Live structured-search outcome:

- `request_id=c4e750dd01ad3bb1ce78621663609d59`
- `actual_cost_usd=0.012`
- Response included `output.content` and `output.grounding`.
- `structured_output.json` preserved normalized `grounding` metadata with `grounding_count=26`.
- Structured `report.md` rendered `## Grounding / Source Review`.

## Artifact Inspection

The initial failed attempt produced no live artifacts because Exa returned `401 Unauthorized` before a response body was available.

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

Real Exa `output.grounding` was observed only in the structured-search response. The normalizer preserved the grounding records as a separate top-level artifact field and did not add grounding fields to the requested schema payload.

The live research response did not include `output.grounding`; this is an observed response-shape result, not a normalizer failure.

## Follow-Up

- Roadmap and tracker docs should now treat `#51` and `#56` as closed/completed.
- Continue to distinguish smoke validation from the bounded live CLI rerun.
- Do not claim S3, Postgres, frontend, deployment, monitor, MCP, agent, or broad production validation from this evidence.
