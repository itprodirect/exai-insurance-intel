# Domain Query Suites

**Benchmark file:** `benchmarks/insurance_cat_queries.json`
**Version:** 2.0.0
**Total queries:** 82 across 8 domain suites + 1 master suite

## Overview

Query suites are versioned, reusable artifacts that define the evaluation surface for insurance and CAT-loss domain intelligence. Each suite targets a specific practitioner type, workflow, or market segment. The shared harness can run any suite via `--suite <name>`.

```bash
python -m exa_demo eval --suite public_adjusters
python -m exa_demo eval --suite all
```

## Suite Reference

### `all` (82 queries)
Master suite combining every query across all domain categories. Used for comprehensive evaluation runs and regression testing.

### `public_adjusters` (10 queries)
**Focus:** Practitioner discovery
Licensed public adjusters — licensing, regulation, fee structures, disciplinary actions, and large-loss specialists. Covers Florida DFS requirements, continuing education, bond requirements, ethics enforcement, and commercial property specialists.

### `cat_law_and_coverage` (13 queries)
**Focus:** Legal research
Property insurance litigation, bad faith, appraisal disputes, AOB, and coverage case law. Includes concurrent causation doctrine, valued policy law, anti-assignment clauses, extracontractual damages, and wind-vs-flood coverage denials.

### `appraisers_and_umpires` (9 queries)
**Focus:** Practitioner discovery
Property damage appraisers, neutral umpires, and appraisal panel professionals. Covers residential and commercial appraisers, Xactimate estimators, umpire selection process, and appraisal award enforcement.

### `independent_adjusters` (9 queries)
**Focus:** Firm and practitioner discovery
Licensed independent adjusters, IA firms, CAT team deployment, and carrier staff augmentation. Includes licensing reciprocity, TWIA certification, multi-state deployment logistics, and commercial large-loss specialists.

### `forensic_and_damage_engineering` (11 queries)
**Focus:** Expert discovery
Forensic engineers, expert witnesses, and technical specialists in wind, water, fire, structural, and building envelope damage. Expanded to include hydrologists, geotechnical engineers (sinkhole), electrical engineers (lightning/surge), and forensic architects (construction defect).

### `restoration_and_mitigation` (10 queries)
**Focus:** Vendor discovery
Field-service vendors and mitigation specialists involved in post-loss response. Covers board-up, water extraction, mold remediation, drying, contents restoration, smoke/soot remediation, IICRC-certified technicians, and catastrophe temporary housing.

### `carrier_tpa_and_vendor_ecosystem` (10 queries)
**Focus:** Firm discovery
Carriers, TPAs, software vendors, managed-repair networks, and insurtech ecosystem discovery. Includes parametric insurance platforms, drone roof inspection tech, fraud detection/SIU vendors, and vendor performance scorecards.

### `regulatory_legislative_and_market_news` (10 queries)
**Focus:** Market watch
Market and regulatory monitoring for Florida insurance and adjacent coverage changes. Expanded beyond Florida to include Louisiana enforcement actions, Texas TWIA, insurance insolvency/guaranty funds, and state climate risk disclosure requirements.

## Query Schema

Each query uses the enhanced format:

```json
{
  "text": "the search query string",
  "topic": "domain category",
  "intent": "what the searcher is trying to accomplish",
  "category": "people | company | news"
}
```

| Field | Description |
|-------|-------------|
| `text` | The actual query string passed to Exa |
| `topic` | Domain area (e.g., "public adjusters", "vendor ecosystem") |
| `intent` | Use-case intent: `people discovery`, `firm discovery`, `vendor discovery`, `expert discovery`, `legal research`, `regulatory lookup`, `market watch`, `software discovery` |
| `category` | Exa search category hint: `people`, `company`, or `news` |

## Versioning

The benchmark file carries a `version` field following semver:
- **Major** bumps when suites are removed or query schema changes
- **Minor** bumps when new suites or queries are added
- **Patch** bumps for wording fixes or metadata corrections

## Changes from v1

- All suites migrated to enhanced format with `description`, `focus`, and per-query metadata
- Removed redundant overlap suites (`coverage_and_litigation`, `adjusters_appraisers_and_restoration`) — their queries now live in the appropriate primary suites
- Renamed `appraisers_umpires_and_restoration` to `appraisers_and_umpires` (restoration queries moved to `restoration_and_mitigation`)
- Added 29 new queries across all suites for deeper domain coverage
- Added `version` field for artifact tracking
