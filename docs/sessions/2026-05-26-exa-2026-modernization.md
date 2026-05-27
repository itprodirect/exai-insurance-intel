# Session: Exa 2026 modernization drift cleanup

- Date: 2026-05-26
- Participants: Codex, user
- Related roadmap items: `#11`, `#17`, `Local #24`
- Related ADRs: [ADR-0002](../adr/ADR-0002-exa-2026-modernization.md)

## Context

Harden Exa request-shape drift before continuing with cost-model and grounding work, while preserving the shipped workflow names and artifact filenames.

## Repo Facts Observed

- User-facing workflows remain `search`, `answer`, `research`, `structured-search`, `find-similar`, `eval`, `compare-search-types`, and `budget`.
- `research` is already implemented as a user-facing workflow backed by `/search` with `type="deep-reasoning"`; it is not posted to a live Exa `/research` endpoint.
- Normal search freshness already maps to `contents.maxAgeHours`; the README still had a `--livecrawl` example.
- `find-similar` accepted `start_crawl_date` and `end_crawl_date` kwargs and previously mapped them to outgoing `startCrawlDate` and `endCrawlDate`.
- The cost model still needs a follow-up pass for current Exa pricing and grounding metadata; this session did not run live Exa calls.

## Decisions Made

- Keep public workflow names and artifact filenames stable.
- Keep supported freshness behavior through `contents.maxAgeHours`.
- Treat find-similar crawl-date kwargs as deprecated compatibility no-ops instead of emitting `startCrawlDate` or `endCrawlDate`.
- Record the modernization boundary in ADR-0002 and docs before deeper cost/grounding work.

## Issues Opened or Updated

- `#11` tracker wording now reflects the current search-backed `research` implementation instead of the old `/research` demo wording.
- `#17` advanced through roadmap, issue-tracker, ADR index, README, and session-note updates.
- `Local #24` documents the Exa 2026 modernization drift cleanup as a local tracker item with GitHub URL still `TBD`.

## Docs Touched

- `README.md`
- `docs/roadmap.md`
- `docs/issue-tracker.md`
- `docs/demo-gallery.md`
- `docs/integration-boundaries.md`
- `docs/adr/README.md`
- `docs/adr/ADR-0002-exa-2026-modernization.md`
- `docs/sessions/2026-05-26-exa-2026-modernization.md`

## Tests and Checks Run

- `python -m pytest -q tests/test_client.py tests/test_workflow_builders.py tests/test_api.py tests/test_cli.py` -> passed (`65 passed`)
- `python -m ruff check .` -> passed
- `python -m pytest -q` -> passed (`277 passed`, one Jupyter path deprecation warning from `jupyter_client`)
- `python scripts/run_live_validation.py --mode smoke` -> passed; wrote smoke artifacts under `live-validation-artifacts/`
- `rg -n --glob 'live-validation-20260527T021418Z-*/*' -- 'livecrawl|highlightsPerUrl|numSentences|startCrawlDate|endCrawlDate' live-validation-artifacts` -> no matches in the current smoke-validation artifact set

## Outcome

- No outgoing request payload path should emit `livecrawl`, `highlightsPerUrl`, `numSentences`, `startCrawlDate`, or `endCrawlDate`.
- README examples now use `--freshness always-live` / `--max-age-hours 0` freshness language instead of `--livecrawl`.
- Docs now consistently describe user-facing `research` as backed by `/search` with `type="deep-reasoning"`.
- No live Exa, S3, Postgres, frontend, or deployed validation was run or claimed in this session.

## Next-Session Handoff

- Recommended next task: reconcile the cost model against current Exa pricing for search-backed `research`, `/answer`, and `/findSimilar`, then normalize modern grounding metadata across artifacts with explicit smoke tests before any live validation claim.
- Keep persistence redesign, frontend redesign, deployment, Monitors, MCP, and Agent API work out of scope unless explicitly requested.
