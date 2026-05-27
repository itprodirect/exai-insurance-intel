from __future__ import annotations

import pytest

from exa_demo.config import default_config, default_pricing
from exa_demo.cost_model import (
    enforce_budget,
    estimate_answer_cost_from_pricing,
    estimate_cost_from_pricing,
    estimate_find_similar_cost_from_pricing,
    estimate_unit_cost_for_config,
)


def test_default_pricing_declares_modern_pricing_keys() -> None:
    pricing = default_pricing()

    assert pricing["standard_search_1_10"] == 0.007
    assert pricing["standard_search_additional_result"] == 0.001
    assert pricing["deep_search_1_10"] == 0.012
    assert pricing["deep_search_additional_result"] == 0.001
    assert pricing["deep_reasoning_search_1_10"] == 0.015
    assert pricing["deep_reasoning_search_additional_result"] == 0.001
    assert pricing["answer"] == 0.005
    assert pricing["find_similar_1_10"] == 0.007
    assert pricing["find_similar_additional_result"] == 0.001
    assert pricing["content_text_per_page"] == 0.001
    assert pricing["content_highlights_per_page"] == 0.001
    assert pricing["content_summary_per_page"] == 0.001


def test_estimate_cost_uses_standard_search_and_included_content_options() -> None:
    pricing = default_pricing()
    payload = {
        "type": "auto",
        "contents": {
            "text": True,
            "highlights": {"maxCharacters": 2666},
        },
    }

    assert estimate_cost_from_pricing(payload, 5, pricing, 100) == 0.007


def test_estimate_cost_charges_summary_as_content_option() -> None:
    pricing = default_pricing()
    payload = {
        "type": "auto",
        "contents": {
            "summary": {"query": "Summarize the result."},
        },
    }

    assert estimate_cost_from_pricing(payload, 5, pricing, 100) == 0.012


def test_estimate_cost_uses_search_type_specific_base_and_additional_results() -> None:
    pricing = default_pricing()

    assert estimate_cost_from_pricing({"type": "deep"}, 12, pricing, 100) == 0.014
    assert estimate_cost_from_pricing({"type": "deep-lite"}, 12, pricing, 100) == 0.014
    assert estimate_cost_from_pricing({"type": "deep-reasoning"}, 12, pricing, 100) == 0.017
    assert estimate_cost_from_pricing({"type": "instant"}, 12, pricing, 100) == 0.009


def test_structured_search_cost_follows_requested_search_type_and_content_options() -> None:
    pricing = default_pricing()
    payload = {
        "type": "deep",
        "outputSchema": {"type": "object"},
        "contents": {
            "text": True,
            "highlights": {"maxCharacters": 2666},
            "summary": {"query": "Summarize each result."},
        },
    }

    assert estimate_cost_from_pricing(payload, 12, pricing, 100) == 0.026


def test_research_estimate_uses_deep_reasoning_search_tier() -> None:
    pricing = default_pricing()
    payload = {
        "type": "deep-reasoning",
        "contents": {"highlights": {"maxCharacters": 2666}},
    }

    assert estimate_cost_from_pricing(payload, 5, pricing, 100) == 0.015


def test_find_similar_cost_is_explicit_and_includes_additional_results() -> None:
    pricing = default_pricing()
    payload = {
        "contents": {
            "text": True,
            "highlights": {"maxCharacters": 2666},
        },
    }

    assert estimate_find_similar_cost_from_pricing(payload, 12, pricing, 100) == 0.009


def test_find_similar_summary_content_adds_per_result_cost() -> None:
    pricing = default_pricing()
    payload = {
        "contents": {
            "text": True,
            "summary": {"query": "Summarize similar pages."},
        },
    }

    assert estimate_find_similar_cost_from_pricing(payload, 12, pricing, 100) == 0.021


def test_answer_estimate_uses_answer_pricing_key() -> None:
    assert estimate_answer_cost_from_pricing(default_pricing()) == 0.005


def test_estimate_unit_cost_for_config_respects_search_type() -> None:
    config = default_config()
    config["search_type"] = "deep-reasoning"
    config["use_highlights"] = False

    assert estimate_unit_cost_for_config(config, default_pricing()) == 0.015


def test_estimate_cost_respects_pricing_overrides() -> None:
    pricing = default_pricing()
    pricing["standard_search_1_10"] = 0.02
    pricing["standard_search_additional_result"] = 0.003
    pricing["content_summary_per_page"] = 0.004
    payload = {
        "type": "auto",
        "contents": {"summary": {"query": "Summarize each result."}},
    }

    assert estimate_cost_from_pricing(payload, 12, pricing, 100) == 0.074


@pytest.mark.parametrize(
    ("search_type", "legacy_key", "override_cost"),
    [
        ("auto", "search_26_100", 0.123),
        ("deep", "deep_search_26_100", 0.234),
        ("deep-reasoning", "deep_reasoning_search_26_100", 0.345),
    ],
)
def test_high_result_estimate_prefers_explicit_legacy_26_100_override(
    search_type: str, legacy_key: str, override_cost: float
) -> None:
    pricing = default_pricing()
    baseline = estimate_cost_from_pricing({"type": search_type}, 30, pricing, 100)
    pricing[legacy_key] = override_cost

    assert estimate_cost_from_pricing({"type": search_type}, 30, pricing, 100) == override_cost
    assert override_cost != baseline


def test_enforce_budget_blocks_projected_overspend() -> None:
    with pytest.raises(RuntimeError, match="Budget cap exceeded"):
        enforce_budget(0.02, spent_usd=0.04, budget_cap_usd=0.05, run_id="demo-run")
