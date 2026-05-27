# ADR-0002: Exa 2026 Request Modernization

- Date: 2026-05-26
- Status: Accepted

## Context

The repo already shipped stable user-facing workflows named `search`, `answer`, `research`, `structured-search`, `find-similar`, `eval`, `compare-search-types`, and `budget`. Exa request-shape guidance has moved away from several older payload fields, and the repo needed to remove drift before continuing with cost-model and grounding work.

The important boundary is that `research` is a product/workflow name in this repo, not proof of a current Exa `/research` wire endpoint.

## Decision

- Keep the public workflow names and artifact filenames stable.
- Keep user-facing `research` backed by `/search` with `type="deep-reasoning"`.
- Estimate user-facing `research` as search-backed `deep-reasoning`, not as Exa's variable-usage `/research` agent endpoint.
- Use `contents.maxAgeHours` for supported freshness behavior, including always-live behavior.
- Do not emit deprecated request payload fields: `livecrawl`, `highlightsPerUrl`, `numSentences`, `startCrawlDate`, or `endCrawlDate`.
- Treat find-similar crawl-date kwargs as deprecated compatibility no-ops instead of mapping them into outgoing request payloads.
- Do not claim live Exa, S3, Postgres, or deployed validation from smoke-only checks.

## Consequences

- Existing CLI/API workflow names remain stable while the transport payloads match the current Exa shape.
- README and docs should describe `research` as search-backed rather than as an Exa `/research` endpoint.
- Freshness docs should prefer `--freshness always-live` or `--max-age-hours 0`; older `--livecrawl` examples should not be used.
- Pricing assumptions should stay centralized in `DEFAULT_PRICING`, remain overrideable from the CLI, and avoid exact live-billing claims unless live Exa `costDollars` fields validate the run.
- Grounding metadata handling is additive to request modernization: keep `output.content` as workflow content and preserve `output.grounding` as separate artifact metadata when present.

## Validation Update - 2026-05-27

- Issue `#51` closed after cost estimates were reconciled around centralized, overrideable pricing assumptions for current search-backed workflows.
- Issue `#56` closed after bounded live CLI validation for `research` and `structured-search`.
- The live `research` rerun completed with results and live cost metadata, but Exa did not return `output.grounding`.
- The live `structured-search` rerun returned both `output.content` and `output.grounding`; the structured artifact recorded `grounding_count=26`, and `report.md` rendered `Grounding / Source Review`.
- This update does not claim S3, Postgres, frontend, deployment, or broad production validation.

## Related Roadmap Items or Issues

- [docs/roadmap.md](../roadmap.md)
- [docs/issue-tracker.md](../issue-tracker.md)
- Local tracker item `#24 Exa 2026 modernization drift cleanup`
