from __future__ import annotations

import math
from typing import Any, Dict, Iterable, Mapping

from .config import DEFAULT_HIGHLIGHT_MAX_CHARACTERS

_STANDARD_SEARCH_TYPES = {"auto", "fast", "instant", "neural", "keyword"}
_DEEP_SEARCH_TYPES = {"deep", "deep-lite", "deep_lite"}
_DEEP_REASONING_SEARCH_TYPES = {"deep-reasoning", "deep_reasoning"}


def estimate_cost_from_pricing(
    payload: Mapping[str, Any],
    num_results: int,
    pricing: Mapping[str, float],
    max_supported_results: int,
) -> float:
    if num_results <= 0:
        raise ValueError("num_results must be >= 1")
    if num_results > int(max_supported_results):
        raise ValueError(
            f"num_results={num_results} exceeds supported estimator range (<= {max_supported_results}). "
            "Lower num_results or update PRICING tiers before running."
        )

    search_type = str(payload.get("type") or "auto").strip().lower()
    search_cost = _resolve_search_cost(search_type, num_results, pricing)
    contents_cost = _estimate_search_backed_contents_cost(payload, num_results, pricing)

    return round(search_cost + contents_cost, 6)


def estimate_answer_cost_from_pricing(pricing: Mapping[str, float]) -> float:
    return round(_pricing_value(pricing, "answer", fallbacks=("answer_1", "answer_1_25")), 6)


def estimate_find_similar_cost_from_pricing(
    payload: Mapping[str, Any],
    num_results: int,
    pricing: Mapping[str, float],
    max_supported_results: int,
) -> float:
    if num_results <= 0:
        raise ValueError("num_results must be >= 1")
    if num_results > int(max_supported_results):
        raise ValueError(
            f"num_results={num_results} exceeds supported estimator range (<= {max_supported_results}). "
            "Lower num_results or update PRICING tiers before running."
        )

    result_cost = _resolve_base_plus_additional_cost(
        prefix="find_similar",
        num_results=num_results,
        pricing=pricing,
        fallbacks=("standard_search", "search"),
    )
    contents_cost = _estimate_search_backed_contents_cost(payload, num_results, pricing)

    return round(result_cost + contents_cost, 6)


def estimate_unit_cost_for_config(
    config: Mapping[str, Any],
    pricing: Mapping[str, float],
) -> float:
    contents: Dict[str, Any] = {}
    if config.get("use_text"):
        contents["text"] = True
    if config.get("use_highlights"):
        contents["highlights"] = {
            "maxCharacters": int(
                config.get("highlight_max_characters")
                or DEFAULT_HIGHLIGHT_MAX_CHARACTERS
            ),
        }
    if config.get("use_summary"):
        contents["summary"] = {
            "query": "Summarize the person's professional background and insurance/CAT relevance."
        }

    payload: Dict[str, Any] = {
        "type": str(config.get("search_type") or "auto"),
    }
    if contents:
        payload["contents"] = contents

    return estimate_cost_from_pricing(
        payload,
        int(config["num_results"]),
        pricing,
        int(config["max_supported_results_for_estimate"]),
    )


def summarize_ledger_rows(rows: Iterable[Mapping[str, Any]]) -> Dict[str, float]:
    request_count = 0
    cache_hits = 0
    uncached_calls = 0
    spent_usd = 0.0
    uncached_total = 0.0

    for row in rows:
        request_count += 1
        cache_hit = int(row.get("cache_hit") or 0) == 1
        if cache_hit:
            cache_hits += 1
            billable_cost = 0.0
        else:
            uncached_calls += 1
            actual_cost = row.get("actual_cost_usd")
            if _has_real_value(actual_cost):
                billable_cost = float(actual_cost)
            else:
                billable_cost = float(row.get("estimated_cost_usd") or 0.0)
            uncached_total += billable_cost
        spent_usd += billable_cost

    avg_uncached = uncached_total / uncached_calls if uncached_calls else 0.0
    return {
        "request_count": int(request_count),
        "cache_hits": int(cache_hits),
        "uncached_calls": int(uncached_calls),
        "spent_usd": round(float(spent_usd), 6),
        "avg_cost_per_uncached_query": round(float(avg_uncached), 6),
    }


def enforce_budget(
    next_estimated_cost: float,
    *,
    spent_usd: float,
    budget_cap_usd: float,
    run_id: str,
) -> None:
    projected_spend = float(spent_usd) + float(next_estimated_cost)
    if projected_spend > float(budget_cap_usd):
        raise RuntimeError(
            "Budget cap exceeded before uncached Exa call.\n"
            f"RUN_ID: {run_id}\n"
            f"Run spend so far: ${float(spent_usd):.4f}\n"
            f"Next call estimate: ${float(next_estimated_cost):.4f}\n"
            f"Cap: ${float(budget_cap_usd):.2f}\n"
            "Lower num_results and/or disable text/summary, or reuse cached queries."
        )


def _has_real_value(value: Any) -> bool:
    if value is None:
        return False
    try:
        return not math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def _resolve_search_cost(
    search_type: str,
    num_results: int,
    pricing: Mapping[str, float],
) -> float:
    group = _search_pricing_group(search_type)
    if group == "deep_reasoning":
        return _resolve_base_plus_additional_cost(
            prefix="deep_reasoning_search",
            num_results=num_results,
            pricing=pricing,
            fallbacks=("deep_search", "standard_search", "search"),
            legacy_type="deep_reasoning",
        )
    if group == "deep":
        return _resolve_base_plus_additional_cost(
            prefix="deep_search",
            num_results=num_results,
            pricing=pricing,
            fallbacks=("standard_search", "search"),
            legacy_type="deep",
        )
    return _resolve_base_plus_additional_cost(
        prefix="standard_search",
        num_results=num_results,
        pricing=pricing,
        fallbacks=("search",),
        legacy_type="standard",
    )


def _search_pricing_group(search_type: str) -> str:
    normalized = str(search_type or "auto").strip().lower()
    normalized_underscore = normalized.replace("-", "_")
    if normalized in _DEEP_REASONING_SEARCH_TYPES or normalized_underscore in _DEEP_REASONING_SEARCH_TYPES:
        return "deep_reasoning"
    if normalized in _DEEP_SEARCH_TYPES or normalized_underscore in _DEEP_SEARCH_TYPES:
        return "deep"
    if normalized in _STANDARD_SEARCH_TYPES or normalized_underscore in _STANDARD_SEARCH_TYPES:
        return "standard"
    return "standard"


def _resolve_base_plus_additional_cost(
    *,
    prefix: str,
    num_results: int,
    pricing: Mapping[str, float],
    fallbacks: tuple[str, ...] = (),
    legacy_type: str | None = None,
) -> float:
    if legacy_type is not None:
        legacy_cost = _resolve_explicit_legacy_high_result_cost(
            legacy_type, num_results, pricing
        )
        if legacy_cost is not None:
            return legacy_cost

    base_key = f"{prefix}_1_10"
    additional_key = f"{prefix}_additional_result"
    if base_key in pricing and additional_key in pricing:
        base_cost = float(pricing[base_key])
        additional_results = max(0, int(num_results) - 10)
        return base_cost + (additional_results * float(pricing[additional_key]))

    for fallback_prefix in fallbacks:
        fallback_base_key = f"{fallback_prefix}_1_10"
        fallback_additional_key = f"{fallback_prefix}_additional_result"
        if fallback_base_key in pricing and fallback_additional_key in pricing:
            base_cost = float(pricing[fallback_base_key])
            additional_results = max(0, int(num_results) - 10)
            return base_cost + (additional_results * float(pricing[fallback_additional_key]))

    if legacy_type is not None:
        return _resolve_legacy_search_cost(legacy_type, num_results, pricing)

    tried = [base_key, additional_key]
    for fallback_prefix in fallbacks:
        tried.extend([f"{fallback_prefix}_1_10", f"{fallback_prefix}_additional_result"])
    raise KeyError(f"Missing pricing for result tier. Tried: {', '.join(tried)}")


def _resolve_explicit_legacy_high_result_cost(
    search_type: str,
    num_results: int,
    pricing: Mapping[str, float],
) -> float | None:
    if int(num_results) <= 25:
        return None

    for key in _explicit_legacy_high_result_cost_keys(search_type):
        if key in pricing:
            return float(pricing[key])
    return None


def _explicit_legacy_high_result_cost_keys(search_type: str) -> list[str]:
    if search_type == "deep_reasoning":
        return ["deep_reasoning_search_26_100", "deep_reasoning_26_100"]
    if search_type == "deep":
        return ["deep_search_26_100"]
    return ["search_26_100"]


def _resolve_legacy_search_cost(
    search_type: str,
    num_results: int,
    pricing: Mapping[str, float],
) -> float:
    tier_suffix = "1_25" if num_results <= 25 else "26_100"
    candidate_keys = _legacy_search_cost_keys(search_type, tier_suffix)

    for key in candidate_keys:
        if key in pricing:
            return float(pricing[key])

    raise KeyError(
        f"Missing pricing for search type '{search_type}' at tier '{tier_suffix}'. "
        f"Tried: {', '.join(candidate_keys)}"
    )


def _legacy_search_cost_keys(search_type: str, tier_suffix: str) -> list[str]:
    candidate_keys: list[str] = []
    if search_type == "deep_reasoning":
        candidate_keys.extend(
            [
                f"deep_reasoning_search_{tier_suffix}",
                f"deep_reasoning_{tier_suffix}",
            ]
        )
    if search_type in {"deep", "deep_reasoning"}:
        candidate_keys.append(f"deep_search_{tier_suffix}")
    candidate_keys.append(f"search_{tier_suffix}")
    return candidate_keys


def _estimate_search_backed_contents_cost(
    payload: Mapping[str, Any],
    num_results: int,
    pricing: Mapping[str, float],
) -> float:
    contents = payload.get("contents")
    if not isinstance(contents, Mapping):
        return 0.0

    # Current search-backed pricing includes text and highlights in the base
    # request cost; AI page summaries remain billed per result/page.
    summary = contents.get("summary")
    if isinstance(summary, Mapping) or summary is True:
        return num_results * float(pricing["content_summary_per_page"])
    return 0.0


def _pricing_value(
    pricing: Mapping[str, float],
    key: str,
    *,
    fallbacks: tuple[str, ...] = (),
) -> float:
    for candidate in (key, *fallbacks):
        if candidate in pricing:
            return float(pricing[candidate])
    raise KeyError(f"Missing pricing key '{key}'. Tried: {', '.join((key, *fallbacks))}")
