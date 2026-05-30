# GitHub Issue Tracker

This document is the canonical mapping between the roadmap in [roadmap.md](./roadmap.md), GitHub issues, ADRs, and session logs.

Update it whenever issues are created, closed, re-scoped, or moved between milestones.

## Tracker Fields

- `Type`: epic or task
- `Milestone`: GitHub milestone the issue belongs to
- `Labels`: normalized labels applied in GitHub
- `Status`: current expected execution state
- `Dependency`: issue number or `None`
- `Source roadmap section`: matching section in [roadmap.md](./roadmap.md)
- `Last-updated session log`: latest repo session note that touched the issue

## Active Backlog

| Issue | Type | Milestone | Labels | Status | Dependency | Source roadmap section | GitHub URL | Last-updated session log |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `#1 Epic: Foundation and experiment discipline` | Epic | `Phase 1 - Foundation` | `type:epic`, `area:core`, `priority:p0`, `status:ready` | Closed | None | Phase 1 - Foundation | `https://github.com/itprodirect/exai-insurance-intel/issues/1` | `docs/sessions/2026-03-18-phase2-parallel-slices.md` |
| `#2 Add normalized typed models for Exa results and cost metadata` | Task | `Phase 1 - Foundation` | `type:task`, `area:core`, `priority:p0`, `status:ready` | Closed | `#1` | Phase 1 - Foundation | `https://github.com/itprodirect/exai-insurance-intel/issues/2` | `docs/sessions/2026-03-18-phase2-parallel-slices.md` |
| `#3 Make exa_demo installable and add CLI entrypoints` | Task | `Phase 1 - Foundation` | `type:task`, `area:core`, `priority:p1`, `status:ready` | Closed | `#1, #2` | Phase 1 - Foundation | `https://github.com/itprodirect/exai-insurance-intel/issues/3` | `docs/sessions/2026-03-18-phase2-parallel-slices.md` |
| `#4 Add experiment artifact logging for auditable runs` | Task | `Phase 1 - Foundation` | `type:task`, `area:eval`, `priority:p0`, `status:ready` | Closed | `#1, #2` | Phase 1 - Foundation | `https://github.com/itprodirect/exai-insurance-intel/issues/4` | `docs/sessions/2026-03-18-phase2-parallel-slices.md` |
| `#5 Expand evaluation taxonomy and before/after reporting` | Task | `Phase 1 - Foundation` | `type:task`, `area:eval`, `priority:p1`, `status:ready` | Closed | `#1, #4` | Phase 1 - Foundation | `https://github.com/itprodirect/exai-insurance-intel/issues/5` | `docs/sessions/2026-03-18-phase2-parallel-slices.md` |
| `#6 Epic: Exa API surface expansion` | Epic | `Phase 2 - Exa Coverage` | `type:epic`, `area:exa-api`, `priority:p0`, `status:ready` | Open | `#1` | Phase 2 - Exa API Coverage | `https://github.com/itprodirect/exai-insurance-intel/issues/6` | `docs/sessions/2026-03-10-roadmap-baseline.md` |
| `#7 Add /answer endpoint demo and cited-answer evaluation` | Task | `Phase 2 - Exa Coverage` | `type:task`, `area:exa-api`, `priority:p0`, `status:ready` | Closed | `#6, #1` | Phase 2 - Exa API Coverage | `https://github.com/itprodirect/exai-insurance-intel/issues/7` | `docs/sessions/2026-03-18-phase2-parallel-slices.md` |
| `#8 Add deep vs deep-reasoning comparison workflow` | Task | `Phase 2 - Exa Coverage` | `type:task`, `area:exa-api`, `priority:p0`, `status:ready` | Closed | `#6, #4` | Phase 2 - Exa API Coverage | `https://github.com/itprodirect/exai-insurance-intel/issues/8` | `docs/sessions/2026-03-18-phase2-parallel-slices.md` |
| `#9 Add structured-output extraction with output_schema` | Task | `Phase 2 - Exa Coverage` | `type:task`, `area:exa-api`, `priority:p1`, `status:ready` | Closed | `#6, #2` | Phase 2 - Exa API Coverage | `https://github.com/itprodirect/exai-insurance-intel/issues/9` | `docs/sessions/2026-03-18-phase2-parallel-slices.md` |
| `#10 Add /findSimilar demo for seed-URL discovery` | Task | `Phase 2 - Exa Coverage` | `type:task`, `area:exa-api`, `priority:p1`, `status:ready` | Closed | `#6, #1` | Phase 2 - Exa API Coverage | `https://github.com/itprodirect/exai-insurance-intel/issues/10` | `docs/sessions/2026-03-18-phase2-parallel-slices.md` |
| `#11 Add research report workflow backed by /search deep-reasoning` | Task | `Phase 2 - Exa Coverage` | `type:task`, `area:exa-api`, `priority:p1`, `status:ready` | Closed | `#6, #2, #4` | Phase 2 - Exa API Coverage | `https://github.com/itprodirect/exai-insurance-intel/issues/11` | `docs/sessions/2026-05-26-exa-2026-modernization.md` |
| `#12 Epic: Insurance/CAT domain coverage` | Epic | `Phase 3 - Domain/Productization` | `type:epic`, `area:domain`, `priority:p1`, `status:ready` | Open | `#1, #6` | Phase 3 - Domain Coverage and Productization | `https://github.com/itprodirect/exai-insurance-intel/issues/12` | `docs/sessions/2026-03-10-roadmap-baseline.md` |
| `#13 Expand domain query suites for PA, CAT law, appraisers, IA, and adjacent industries` | Task | `Phase 3 - Domain/Productization` | `type:task`, `area:domain`, `priority:p0`, `status:ready` | Closed | `#12, #4, #5` | Phase 3 - Domain Coverage and Productization | `https://github.com/itprodirect/exai-insurance-intel/issues/13` | `docs/sessions/2026-03-19-phase3-research-benchmarks-rails.md` |
| `#14 Add export/report outputs and demo-gallery documentation` | Task | `Phase 3 - Domain/Productization` | `type:task`, `area:docs`, `priority:p1`, `status:ready` | Closed | `#12, #7, #8, #13` | Phase 3 - Domain Coverage and Productization | `https://github.com/itprodirect/exai-insurance-intel/issues/14` | `docs/sessions/2026-04-11-issue-14-report-export.md` |
| `#15 Epic: Documentation, governance, and repo operations` | Epic | `Phase 3 - Domain/Productization` | `type:epic`, `area:ops`, `priority:p0`, `status:ready` | Open | None | Phase 4 - Documentation, Governance, and Repo Operations | `https://github.com/itprodirect/exai-insurance-intel/issues/15` | `docs/sessions/2026-03-10-roadmap-baseline.md` |
| `#16 Extend CI/security hardening and document integration follow-ons` | Task | `Phase 3 - Domain/Productization` | `type:task`, `area:ops`, `priority:p1`, `status:ready` | In progress | `#15, #14` | Phase 3 - Domain Coverage and Productization | `https://github.com/itprodirect/exai-insurance-intel/issues/16` | `docs/sessions/2026-03-21-payload-boundary-cleanup.md` |
| `#17 Maintain roadmap, issue tracker, ADRs, and session notes` | Task | `Phase 3 - Domain/Productization` | `type:task`, `area:docs`, `priority:p0`, `status:ready` | In progress | `#15` | Phase 4 - Documentation, Governance, and Repo Operations | `https://github.com/itprodirect/exai-insurance-intel/issues/17` | `docs/sessions/2026-05-30-issue-65-docs-hardening-queue.md` |
| `#18 Upgrade README with feature matrix, architecture diagram, and roadmap links` | Task | `Phase 3 - Domain/Productization` | `type:task`, `area:docs`, `priority:p1`, `status:ready` | Closed | `#15` | Phase 4 - Documentation, Governance, and Repo Operations | `https://github.com/itprodirect/exai-insurance-intel/issues/18` | `docs/sessions/2026-03-18-phase2-parallel-slices.md` |
| `Local #24 Exa 2026 modernization drift cleanup` | Task | `Phase 2 - Exa Coverage` | `type:task`, `area:exa-api`, `priority:p0`, `status:done` | Done | `#6, #11` | Phase 2 - Exa API Coverage | TBD | `docs/sessions/2026-05-26-exa-2026-modernization.md` |
| `#51 Reconcile Exa cost model for current pricing and modern workflows` | Task | None | `type:task`, `area:exa-api`, `priority:p1`, `status:ready` | Closed | `#6, #11, Local #24` | Phase 2 - Exa API Coverage | `https://github.com/itprodirect/exai-insurance-intel/issues/51` | `docs/sessions/2026-05-27-live-grounding-validation.md` |
| `#56 Validate live Exa grounding variants for research and structured-search` | Task | None | `type:task`, `area:exa-api`, `priority:p1`, `status:ready` | Closed | `#6, #11, #51` | Phase 2 - Exa API Coverage | `https://github.com/itprodirect/exai-insurance-intel/issues/56` | `docs/sessions/2026-05-27-live-grounding-validation.md` |

Issue `#11` originally used `/research` wording in the planning/demo sense. The current implementation keeps the user-facing `research` workflow name, but the Exa request path is `/search` with `type="deep-reasoning"`, not a live Exa `/research` endpoint.

`Local #24` captures the Exa 2026 modernization cleanup completed before the cost/grounding slice. Issue `#51` closed the cost-model reconciliation, and issue `#56` closed the bounded live grounding validation for CLI `research` and `structured-search`. Do not restore deprecated payload fields, and do not treat the bounded live CLI evidence as S3, Postgres, frontend, deployment, or broad production validation.

## Phase 5 - Pilot Web Product

| Issue | Type | Milestone | Labels | Status | Dependency | Source roadmap section | GitHub URL | Last-updated session log |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `#19 Epic: Pilot web product layer` | Epic | `Phase 5 - Pilot` | `type:epic`, `area:pilot`, `priority:p0`, `status:ready` | Open | Phases 1-4 | Phase 5 - Pilot Web Product | TBD | `docs/sessions/2026-03-22-pilot-alignment.md` |
| `#20 Thin FastAPI wrapper over existing workflows` | Task | `Phase 5 - Pilot` | `type:task`, `area:api`, `priority:p0`, `status:done` | Done | `#19` | Phase 5 Level 1 | TBD | `docs/sessions/2026-03-22-api-wrapper.md` |
| `#21 Frontend app shell (Next.js + Tailwind + shadcn/ui)` | Task | `Phase 5 - Pilot` | `type:task`, `area:frontend`, `priority:p0`, `status:done` | Done | `#19, #20` | Phase 5 Level 1 | TBD | `docs/sessions/2026-03-22-frontend-shell.md` |
| `#22 Pilot auth + request/budget boundary controls` | Task | `Phase 5 - Pilot` | `type:task`, `area:auth`, `priority:p0`, `status:done` | Done | `#19, #20` | Phase 5 Level 1 | TBD | `docs/sessions/2026-04-11-issue-22-run-pagination-bounds.md` |
| `#23 Persistence/state baseline (S3 artifacts + Postgres usage)` | Task | `Phase 5 - Pilot` | `type:task`, `area:infra`, `priority:p1`, `status:ready` | In progress | `#19, #20` | Phase 5 Level 1 | TBD | `docs/sessions/2026-05-29-issue-63-s3-postgres-validation.md` |

### Pilot Hardening Queue (GitHub `#60`-`#65`)

These GitHub issues are the ordered Phase 5 Level 1 pilot hardening queue. Future sessions should use this queue instead of treating the original setup slices below as immediate next work.

| GitHub issue | Status | Scope | Current guidance |
| --- | --- | --- | --- |
| [`#60 Preserve query params in frontend API proxy`](https://github.com/itprodirect/exai-insurance-intel/issues/60) | Closed | Preserve query parameters when the frontend proxy forwards API requests | Completed hardening slice. Do not reopen unless a new proxy regression is found. |
| [`#61 Replace interactive frontend lint command`](https://github.com/itprodirect/exai-insurance-intel/issues/61) | Closed | Replace the interactive frontend lint path with a non-interactive command | Completed hardening slice. Keep future frontend lint guidance non-interactive. |
| [`#62 Add frontend build and lint coverage to CI`](https://github.com/itprodirect/exai-insurance-intel/issues/62) | Closed | Add frontend build and lint coverage to CI | Completed hardening slice. Treat frontend CI coverage as present unless current workflow evidence shows drift. |
| [`#63 Add bounded S3/Postgres persistence validation`](https://github.com/itprodirect/exai-insurance-intel/issues/63) | Closed | Add a bounded real-service validation command for pilot S3/Postgres persistence | Completed command/runbook slice. It does not claim real S3/Postgres validation unless the command is run successfully with real services and credentials. |
| [`#64 Add fail-closed auth guard for pilot deployment mode`](https://github.com/itprodirect/exai-insurance-intel/issues/64) | Closed | Add fail-closed auth guard behavior for pilot deployment mode | Completed hardening slice. Do not widen auth scope or deployment behavior without explicit follow-up inspection. |
| [`#65 Refresh current docs for the new hardening queue`](https://github.com/itprodirect/exai-insurance-intel/issues/65) | Open / current | Refresh current docs so future agents see the ordered hardening queue and completion state | Final docs cleanup slice for this queue. Keep changes docs-only and evidence-based. |

### Phase 5 Level 1 Setup Slices

1. ~~**Slice 1: Thin API wrapper** (`#20`)~~ — Done. FastAPI app at `src/exa_demo/api.py` with 5 POST endpoints + health. 9 smoke-mode tests.
2. ~~**Slice 2: Frontend app shell** (`#21`)~~ — Done. Next.js app in `frontend/` with search, answer, research panels. Server-side proxy to backend.
3. ~~**Slice 3: Pilot auth + boundary controls** (`#22`)~~ — Done. Owner-or-ops record access, multi-user rate-limit isolation, saved-query input bounds, and run-pagination bounds are shipped.
4. **Slice 4: Persistence baseline** (`#23`) - In progress. S3 artifact-location persistence, Postgres repository/factory coverage, backend factory logging, optional pilot dependency extras, health backend labels, and a bounded real S3/Postgres validation command/runbook are present; external S3/Postgres execution evidence still requires real services and credentials.

These setup slices remain the local Phase 5 roadmap state, not the immediate hardening queue. Each new slice should still be one focused agent session. See [agent-execution-defaults.md](./agent-execution-defaults.md) for session rules.

## Usage Rules

- Every active roadmap item outside Phase 0 should map to exactly one GitHub issue. If the mapping does not exist yet, leave the GitHub URL as `TBD` and document the drift explicitly.
- Close the roadmap item and issue together, or document why they diverged.
- Update the `Last-updated session log` field whenever the issue scope, status, or acceptance criteria changes.
- Record durable process changes in `docs/adr/`.

## Phase 5 Numbering Note

- The Phase 5 local tracker IDs `#19`-`#23` are roadmap/task IDs used in repo docs.
- GitHub issue numbers `22` and `23` are already occupied by older merged PRs, so the `GitHub URL` field for the local Phase 5 `#22` and `#23` items remains `TBD` until dedicated GitHub issues are created.
- GitHub issue numbers `#60`-`#65` are the actual pilot hardening queue issues and are separate from the local Phase 5 roadmap IDs.
