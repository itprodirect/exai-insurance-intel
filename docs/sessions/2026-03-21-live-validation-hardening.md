# Session: Live Validation Hardening

- Date: 2026-03-21
- Participants: User, Codex
- Related roadmap items: `#16`, `#17`
- Related ADRs: none

## Context

Harden the manual live-validation runner so it verifies artifact contracts instead of treating subprocess success as sufficient, while keeping the docs and tracker aligned with the new behavior.

## Repo Facts Observed

- `docs/integration-boundaries.md` already describes smoke-first CI, explicit manual live validation, and runtime artifacts.
- `scripts/run_live_validation.py` is the manual validation entrypoint referenced by the docs.
- `scripts/run_live_validation.py` previously checked subprocess exit status and JSON parsing, but it did not assert that each workflow emitted the expected artifact files or live request identifiers.
- `tests/test_scripts.py` already covered the script entrypoints and was the natural place to pin the new runner behavior.
- `docs/issue-tracker.md` still has `#16` and `#17` in progress, with the latest session log pointer from the prior refactor pass.

## Decisions Made

- Keep the validation command set and smoke-first boundary unchanged.
- Tighten the manual live-validation runner around explicit payload-key, artifact-file, and live-mode `request_id` assertions.
- Tighten the written live-validation boundary around explicit live-mode guardrails and artifact-contract assertions.
- Update tracker pointers so the active ops/docs issues point at this session rather than the prior refactor session.

## Issues Opened or Updated

- `#16 Extend CI/security hardening and document integration follow-ons`: advanced through manual live-validation contract hardening and session log pointer updated to this session.
- `#17 Maintain roadmap, issue tracker, ADRs, and session notes`: session log pointer updated to this session.

## Files Touched

- `scripts/run_live_validation.py`
- `tests/test_scripts.py`
- `docs/integration-boundaries.md`
- `docs/issue-tracker.md`
- `docs/sessions/2026-03-21-live-validation-hardening.md`

## Tests and Checks Run

- `python -m pytest -q tests/test_scripts.py`
- `python -m ruff check scripts/run_live_validation.py tests/test_scripts.py`
- `python -m pytest -q`
- `python -m ruff check .`
- `python scripts/run_live_validation.py --mode smoke --run-id-prefix local-ci-hardening`

## Outcome

- Manual live validation now fails if a workflow emits the wrong top-level contract, misses its expected artifact files, or omits `request_id` in live mode for single-workflow commands.
- Clarified that manual live validation should fail closed in live mode without `EXA_API_KEY`.
- Added explicit artifact-contract expectations for manual live validation runs.
- Kept the repo history aligned by updating the active issue tracker session pointers.

## Next-Session Handoff

- If the live-validation boundary changes again, update both the runner assertions and the integration doc in the same session.
- Any future code hardening should keep the manual validation flow bounded and treat artifact assertions as part of the acceptance criteria.
