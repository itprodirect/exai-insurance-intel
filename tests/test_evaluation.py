from __future__ import annotations

from dataclasses import dataclass

import json

from exa_demo.evaluation import (
    DEFAULT_RELEVANCE_KEYWORDS,
    evaluate_batch_queries,
    load_benchmark_queries,
    load_benchmark_suites,
)
from exa_demo.models import QueryEvaluationRecord


@dataclass
class FakeMeta:
    cache_hit: bool
    estimated_cost_usd: float
    actual_cost_usd: float | None
    request_hash: str = 'hash-123'
    request_payload: dict | None = None
    request_id: str | None = 'req-123'
    resolved_search_type: str | None = 'auto'
    created_at_utc: str = '2026-03-10T00:00:00+00:00'


def test_load_benchmark_queries_matches_current_fixture() -> None:
    queries = load_benchmark_queries()

    assert len(queries) == 15
    assert queries[0].startswith("forensic engineer wind damage expert witness")
    assert queries[-1].startswith("civil engineer structural damage assessment")


def test_load_benchmark_queries_can_target_named_suite() -> None:
    all_queries = load_benchmark_queries(suite="all")
    engineering_queries = load_benchmark_queries(suite="forensic_and_damage_engineering")
    suites = load_benchmark_suites()

    assert len(all_queries) == 15
    assert len(engineering_queries) == 5
    assert suites["coverage_and_litigation"][0].startswith("policyholder attorney")
    assert suites["adjusters_appraisers_and_restoration"][-1].startswith("civil engineer structural")


def test_load_benchmark_queries_supports_legacy_list_fixtures(tmp_path) -> None:
    legacy_path = tmp_path / "legacy_queries.json"
    legacy_queries = ["one query", "two query"]
    legacy_path.write_text(json.dumps(legacy_queries), encoding="utf-8")

    assert load_benchmark_suites(legacy_path) == {"default": legacy_queries}
    assert load_benchmark_queries(legacy_path) == legacy_queries


def test_evaluate_batch_queries_builds_expected_flags() -> None:
    def fake_search_people(query: str, *, num_results: int):
        return (
            {
                "results": [
                    {
                        "title": f"{query} insurance expert witness",
                        "url": "https://www.linkedin.com/in/test-person",
                        "highlights": ["forensic insurance litigation profile"],
                    }
                ]
            },
            FakeMeta(cache_hit=False, estimated_cost_usd=0.01, actual_cost_usd=0.02, request_payload={"query": query}),
        )

    df = evaluate_batch_queries(
        ["query one"],
        search_people=fake_search_people,
        num_results=5,
        relevance_keywords=DEFAULT_RELEVANCE_KEYWORDS,
        redact_text=lambda value: value,
        extract_preview=lambda row, max_chars: " | ".join(row.get("highlights", []))[:max_chars],
    )

    row = df.iloc[0].to_dict()
    assert row["linkedin_present"] is True
    assert row["relevance_keywords_present"] is True
    assert row["top_url"] == "https://www.linkedin.com/in/test-person"
    assert row["top_preview"] == "forensic insurance litigation profile"
    assert row["request_hash"] == 'hash-123'
    assert row["relevance_score"] == 1.0
    assert row["credibility_score"] == 1.0
    assert row["actionability_score"] >= 0.0
    assert row["confidence_score"] >= 0.5
    assert row["failure_reasons"] == []


def test_evaluate_batch_queries_marks_no_results_failure() -> None:
    def fake_search_people(query: str, *, num_results: int):
        return (
            {"results": []},
            FakeMeta(cache_hit=False, estimated_cost_usd=0.01, actual_cost_usd=0.0, request_payload={"query": query}),
        )

    df = evaluate_batch_queries(
        ["query one"],
        search_people=fake_search_people,
        num_results=5,
        relevance_keywords=DEFAULT_RELEVANCE_KEYWORDS,
        redact_text=lambda value: value,
        extract_preview=lambda row, max_chars: "",
    )

    row = df.iloc[0].to_dict()
    assert row["result_count"] == 0
    assert row["failure_reasons"] == ["no_results"]
    assert row["primary_failure_reason"] == "no_results"


def test_evaluate_batch_queries_can_emit_structured_records() -> None:
    emitted: list[QueryEvaluationRecord] = []

    def fake_search_people(query: str, *, num_results: int):
        return (
            {
                "results": [
                    {
                        "title": f"{query} insurance expert witness",
                        "url": "https://www.linkedin.com/in/test-person",
                        "highlights": ["forensic insurance litigation profile"],
                    }
                ],
                "costDollars": {"search": 0.005, "contents": 0.001, "total": 0.006},
            },
            FakeMeta(cache_hit=True, estimated_cost_usd=0.01, actual_cost_usd=0.0, request_payload={"query": query}),
        )

    evaluate_batch_queries(
        ["query one"],
        search_people=fake_search_people,
        num_results=5,
        relevance_keywords=DEFAULT_RELEVANCE_KEYWORDS,
        redact_text=lambda value: value,
        extract_preview=lambda row, max_chars: " | ".join(row.get("highlights", []))[:max_chars],
        record_query=emitted.append,
    )

    assert len(emitted) == 1
    assert emitted[0].query == 'query one'
    assert emitted[0].cache_hit is True
    assert emitted[0].results[0].url == 'https://www.linkedin.com/in/test-person'
    assert emitted[0].cost_breakdown.total == 0.006
    assert emitted[0].failure_reasons == []
    assert emitted[0].primary_failure_reason is None
