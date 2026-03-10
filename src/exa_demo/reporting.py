from __future__ import annotations

from typing import Any, Dict, List, Mapping

import pandas as pd

from .cost_model import estimate_unit_cost_for_config


def build_qualitative_notes(
    batch_df: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    smoke_no_network: bool,
) -> List[str]:
    notes: List[str] = []
    if not batch_df.empty:
        relevance_rate = float(batch_df["relevance_keywords_present"].mean())
        linkedin_rate = float(batch_df["linkedin_present"].mean())
        avg_results = float(batch_df["result_count"].mean())
        notes.append(f"Relevance-keyword signal rate: {relevance_rate:.0%}.")
        notes.append(f"LinkedIn profile signal present in: {linkedin_rate:.0%} of queries.")
        notes.append(f"Average results returned per query: {avg_results:.1f} (num_results={config['num_results']}).")
    else:
        notes.append("No batch results yet. Run Cell 6.")

    if config["use_text"]:
        notes.append("Text is enabled: better evidence depth but higher spend.")
    else:
        notes.append("Text is disabled: cheaper baseline; highlights are usually enough for triage.")

    if config["use_summary"]:
        notes.append("Summary is enabled: validate value before scaling due to extra cost.")
    else:
        notes.append("Summary is disabled (recommended baseline for low-cost evaluation).")

    if smoke_no_network:
        notes.append("Smoke mode active: results are mocked and costs are zero.")

    return notes


def build_cost_projections(
    summary_metrics: Mapping[str, Any],
    *,
    config: Mapping[str, Any],
    pricing: Mapping[str, float],
) -> Dict[str, Any]:
    projection_basis = "observed_avg_uncached"
    projection_unit_cost = float(summary_metrics.get("avg_cost_per_uncached_query", 0.0))
    if projection_unit_cost <= 0:
        projection_unit_cost = estimate_unit_cost_for_config(config, pricing)
        projection_basis = "estimated_from_current_config"

    return {
        "projection_basis": projection_basis,
        "unit_cost_usd": round(projection_unit_cost, 6),
        "projected_100_queries_usd": round(projection_unit_cost * 100, 4),
        "projected_1000_queries_usd": round(projection_unit_cost * 1000, 4),
        "projected_10000_queries_usd": round(projection_unit_cost * 10000, 4),
    }


def recommendation(
    summary_metrics: Mapping[str, Any],
    batch_df: pd.DataFrame,
    *,
    run_id: str,
    budget_cap_usd: float,
    smoke_no_network: bool,
) -> Dict[str, Any]:
    if batch_df.empty:
        relevance_rate = 0.0
        linkedin_rate = 0.0
    else:
        relevance_rate = float(batch_df["relevance_keywords_present"].mean())
        linkedin_rate = float(batch_df["linkedin_present"].mean())

    avg_cost = float(summary_metrics.get("avg_cost_per_uncached_query", 0.0))

    headline = "Integrate only for scoped workflows"
    if relevance_rate >= 0.70 and (avg_cost <= 0.02 or smoke_no_network):
        headline = "Integrate (with human review and budget guards)"
    if relevance_rate < 0.50 or avg_cost > 0.05:
        headline = "Do not integrate at current settings"

    return {
        "run_id": run_id,
        "headline_recommendation": headline,
        "observed_relevance_rate": round(relevance_rate, 3),
        "observed_linkedin_rate": round(linkedin_rate, 3),
        "avg_cost_per_uncached_query_usd": round(avg_cost, 4),
        "budget_cap_usd": float(budget_cap_usd),
        "safety_guardrails": [
            "Public/professional info only",
            "No address hunting or contact harvesting",
            "Keep redaction enabled for displayed snippets",
            "Human review required before operational use",
        ],
        "integration_points": [
            {
                "workflow": "Expert/professional discovery",
                "value": "Find candidate experts and collect source URLs + short relevance snippets for analyst review.",
                "safe_pattern": "Query by role + peril + jurisdiction; keep outputs to title/url/highlights by default.",
            },
            {
                "workflow": "Consultant/witness context enrichment",
                "value": "When reports name professionals, quickly pull public bios/publications for context.",
                "safe_pattern": "Search by name + role + insurance/litigation terms; do not harvest personal contact data.",
            },
            {
                "workflow": "Claim dispute research triage",
                "value": "Identify relevant disciplines (forensic engineer, meteorologist, accountant, etc.) fast.",
                "safe_pattern": "Use highlights-on/text-off baseline; selectively deepen only shortlisted results.",
            },
        ],
        "next_tuning_moves": [
            "Keep highlights on, text off, summary off, num_results=5 for baseline cost testing.",
            "Use include_domains only when you need tighter source control.",
            "Enable text/summary only in second-pass review workflows.",
        ],
    }