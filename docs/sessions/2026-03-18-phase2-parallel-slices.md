# Session: Phase 2 Parallel Slice Delivery

- Date: 2026-03-18
- Participants: User, Codex, subagents
- Related roadmap items: `#8`, `#13`, `#16`, `#17`
- Related ADRs: none

## Context

Kick off a slice-based implementation session that keeps code, tests, docs, commits, and pushes synchronized after each completed slice.

## Repo Facts Observed

- The repo started this session clean on `main`.
- CI in [ci.yml](C:\Users\user\Desktop\exai-search-demo\.github\workflows\ci.yml) only ran the notebook smoke workflow.
- `pytest -q` passed locally at session start with 20 tests.
- The current harness already had CLI coverage for `search`, `eval`, and `budget`, but no direct test coverage for the helper scripts under `scripts/`.

## Decisions Made

- Deliver work in bounded slices and keep docs/tests/commits/pushes aligned per slice instead of batching all changes at the end.
- Take CI and test hardening first so later API-surface work lands on safer rails.
- Treat generated experiment artifacts from smoke validation as disposable runtime output, not source-controlled session deliverables.

## Issues Opened or Updated

- `#16 Extend CI/security hardening and document integration follow-ons`: moved to `In progress` for pytest-in-CI and script/negative-path coverage work.
- `#8 Add deep vs deep-reasoning comparison workflow`: moved to `In progress` after landing additive deep-search request shaping and type-aware cost controls.

## Docs Touched

- `docs/issue-tracker.md`
- `docs/sessions/2026-03-18-phase2-parallel-slices.md`
- `README.md`

## Tests and Checks Run

- `pytest -q` -> passed at session start with `20 passed`.
- `pytest -q tests\test_cli.py tests\test_scripts.py` -> passed after adding negative-path and script coverage.
- `pytest -q` -> passed after slice-1 changes with `27 passed`.
- `python scripts/run_notebook_smoke.py --mode smoke` -> passed.
- `pytest -q tests\test_client.py tests\test_models.py` -> passed for deep-search payload controls.
- `pytest -q tests\test_cost_model.py tests\test_cli.py` -> passed for deep-search CLI and cost controls.
- `pytest -q` -> passed after slice-2 integration with `33 passed`.

## Outcome

- Completed slice 1 CI/test hardening in two commits:
  - `92e840f` added CLI negative-path coverage and new script tests.
  - A follow-up commit is expected to land CI pytest execution, pytest warning cleanup, and the docs/session updates from this log.
- CI now runs both `pytest` and notebook smoke so later feature slices land on safer rails.
- Completed slice 2 deep-search rail building in two commits:
  - `28428e9` added additive payload controls for `additionalQueries`, published-date filters, and `livecrawl`.
  - `3f39c3d` added CLI flags and type-aware cost override support for `deep` and `deep-reasoning` experiments.
- The repo can now run deeper `/search` experiments without changing the existing `results[]` artifact and evaluation contract.

## Next-Session Handoff

- Start slice 3 on grouped comparison reporting and richer query-suite segmentation.
- Fold the deep-search controls into before/after reporting so cost and quality deltas are visible by search type and query family.
