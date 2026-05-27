from __future__ import annotations

from exa_demo.client import (
    build_answer_payload,
    build_exa_payload,
    build_find_similar_payload,
    build_research_payload,
    build_structured_search_payload,
    exa_answer,
    exa_find_similar,
    exa_research,
    exa_search_people,
    exa_structured_search,
    mock_exa_answer_response,
    mock_exa_find_similar_response,
    mock_exa_response,
    mock_exa_research_response,
    mock_exa_structured_search_response,
)
from exa_demo.config import default_config
from exa_demo.config import default_pricing


class FakeCacheStore:
    def __init__(self) -> None:
        self.calls = []

    def get_or_set(self, payload, estimated_cost, *, run_id, budget_cap_usd, fetcher, response_filter=None):
        self.calls.append(
            {
                "payload": payload,
                "estimated_cost": estimated_cost,
                "run_id": run_id,
                "budget_cap_usd": budget_cap_usd,
            }
        )
        result = fetcher(payload)
        if response_filter is not None:
            result = response_filter(result)
        return result, False


DEPRECATED_REQUEST_FIELDS = {"livecrawl", "highlightsPerUrl", "numSentences"}


def assert_no_deprecated_request_fields(value) -> None:
    if isinstance(value, dict):
        assert DEPRECATED_REQUEST_FIELDS.isdisjoint(value)
        for item in value.values():
            assert_no_deprecated_request_fields(item)
    elif isinstance(value, list):
        for item in value:
            assert_no_deprecated_request_fields(item)


def test_build_exa_payload_includes_additive_deep_search_fields() -> None:
    config = default_config()
    config.update(
        {
            "additional_queries": [
                "licensed public adjuster Florida",
                "  catastrophe claims expert witness  ",
                "",
            ],
            "start_published_date": "2026-01-01",
            "end_published_date": "2026-03-01",
            "max_age_hours": 0,
        }
    )

    payload = build_exa_payload("insurance expert witness", config, num_results=3)

    assert payload["query"] == "insurance expert witness"
    assert payload["numResults"] == 3
    assert payload["additionalQueries"] == [
        "licensed public adjuster Florida",
        "catastrophe claims expert witness",
    ]
    assert payload["startPublishedDate"] == "2026-01-01"
    assert payload["endPublishedDate"] == "2026-03-01"
    assert payload["contents"]["maxAgeHours"] == 0
    assert payload["contents"]["highlights"] == {"maxCharacters": 2666}
    assert_no_deprecated_request_fields(payload)
    assert "results" not in payload


def test_build_exa_payload_leaves_additive_fields_out_by_default() -> None:
    config = default_config()

    payload = build_exa_payload("insurance expert witness", config)

    assert "additionalQueries" not in payload
    assert "startPublishedDate" not in payload
    assert "endPublishedDate" not in payload
    assert "livecrawl" not in payload
    assert "maxAgeHours" not in payload["contents"]
    assert payload["contents"]["highlights"] == {"maxCharacters": 2666}
    assert_no_deprecated_request_fields(payload)


def test_mock_exa_response_preserves_search_result_shape_with_additive_controls() -> None:
    payload = build_exa_payload(
        "insurance expert witness",
        {
            **default_config(),
            "additional_queries": ["licensed public adjuster Florida"],
            "start_published_date": "2026-01-01",
            "end_published_date": "2026-03-01",
            "max_age_hours": 0,
        },
    )

    response = mock_exa_response(payload)

    assert response["searchType"] == "auto"
    assert response["requestId"].startswith("smoke-")
    assert response["costDollars"]["total"] == 0.0
    assert isinstance(response["results"], list)
    assert len(response["results"]) == payload["numResults"]
    assert response["results"][0]["title"].startswith("Mock Professional Result")


def test_build_find_similar_payload_includes_similarity_controls() -> None:
    config = default_config()
    config.update(
        {
            "include_domains": ["example.com"],
            "exclude_domains": ["badexample.com"],
            "moderation": False,
        }
    )

    payload = build_find_similar_payload(
        "https://example.com/article",
        config,
        num_results=3,
        start_crawl_date="2026-01-01",
        end_crawl_date="2026-03-01",
        start_published_date="2026-01-15",
        end_published_date="2026-03-15",
        exclude_source_domain=True,
        text=True,
        highlights={"highlightsPerUrl": 2, "numSentences": 1},
        context=True,
    )

    assert payload["url"] == "https://example.com/article"
    assert payload["numResults"] == 3
    assert payload["includeDomains"] == ["example.com"]
    assert payload["excludeDomains"] == ["badexample.com"]
    assert payload["startCrawlDate"] == "2026-01-01"
    assert payload["endCrawlDate"] == "2026-03-01"
    assert payload["startPublishedDate"] == "2026-01-15"
    assert payload["endPublishedDate"] == "2026-03-15"
    assert payload["excludeSourceDomain"] is True
    assert payload["moderation"] is False
    assert payload["contents"]["text"] is True
    assert payload["contents"]["highlights"] == {"maxCharacters": 1333}
    assert payload["contents"]["context"] is True
    assert_no_deprecated_request_fields(payload)


def test_mock_exa_find_similar_response_returns_context_and_text() -> None:
    payload = build_find_similar_payload(
        "https://example.com/article",
        default_config(),
        exclude_source_domain=True,
        text=True,
        highlights=True,
        context=True,
    )

    response = mock_exa_find_similar_response(payload)

    assert isinstance(response["results"], list)
    assert len(response["results"]) == payload["numResults"]
    assert response["context"].startswith("Mock context for seed URL https://example.com/article")
    assert response["results"][0]["text"].startswith("Mock similar text for seed URL:")
    assert response["results"][0]["highlights"][0].startswith("Mock highlight for seed URL:")
    assert response["results"][0]["url"].split("/")[2].startswith("related-")


def test_build_structured_search_payload_adds_output_schema() -> None:
    config = default_config()
    config.update(
        {
            "additional_queries": ["licensed public adjuster Florida"],
            "max_age_hours": 0,
        }
    )
    output_schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "professionals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "role": {"type": "string"},
                    },
                },
            },
        },
    }

    payload = build_structured_search_payload(
        "insurance expert witness",
        config,
        output_schema,
        num_results=2,
    )

    assert payload["query"] == "insurance expert witness"
    assert payload["numResults"] == 2
    assert payload["additionalQueries"] == ["licensed public adjuster Florida"]
    assert payload["contents"]["maxAgeHours"] == 0
    assert payload["contents"]["highlights"] == {"maxCharacters": 2666}
    assert payload["outputSchema"] == output_schema
    assert_no_deprecated_request_fields(payload)


def test_mock_exa_structured_search_response_returns_structured_output() -> None:
    payload = build_structured_search_payload(
        "insurance expert witness",
        default_config(),
        {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "professionals": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "role": {"type": "string"},
                        },
                    },
                },
            },
        },
    )

    response = mock_exa_structured_search_response(payload)

    assert response["searchType"] == "auto"
    assert response["structuredOutput"]["summary"].startswith("Mock summary for query:")
    assert response["structuredOutput"]["professionals"][0]["name"].startswith("Mock name for query:")
    assert response["output"]["content"] == response["structuredOutput"]
    assert response["output"]["grounding"][0]["url"].startswith("https://www.linkedin.com/")
    assert len(response["results"]) == payload["numResults"]


def test_build_answer_payload_is_query_only() -> None:
    payload = build_answer_payload("What is the Florida appraisal clause dispute process?")

    assert payload == {"query": "What is the Florida appraisal clause dispute process?", "text": True}


def test_mock_exa_answer_response_returns_citations() -> None:
    payload = build_answer_payload("What is the Florida appraisal clause dispute process?")

    response = mock_exa_answer_response(payload)

    assert response["answer"].startswith("Mock answer for query:")
    assert isinstance(response["citations"], list)
    assert len(response["citations"]) == 2
    assert response["citations"][0]["url"].startswith("https://example.com/mock-answer/")


def test_build_research_payload_uses_deep_reasoning_search_shape() -> None:
    payload = build_research_payload(
        "Summarize the Florida CAT market outlook.",
        default_config(),
    )

    assert payload["query"] == "Summarize the Florida CAT market outlook."
    assert payload["type"] == "deep-reasoning"
    assert payload["numResults"] == 5
    assert payload["contents"]["highlights"] == {"maxCharacters": 2666}
    assert_no_deprecated_request_fields(payload)


def test_mock_exa_research_response_returns_search_results() -> None:
    payload = build_research_payload(
        "Summarize the Florida CAT market outlook.",
        default_config(),
    )

    response = mock_exa_research_response(payload)

    assert response["searchType"] == "deep-reasoning"
    assert isinstance(response["results"], list)
    assert len(response["results"]) == 5
    assert response["results"][0]["url"].startswith("https://example.com/mock-research/")
    assert response["output"]["content"].startswith("Search-backed research report.")
    assert response["output"]["grounding"][0]["title"] == "Mock Research Source 1"
    assert "report" not in response
    assert "citations" not in response


def test_exa_answer_uses_smoke_cited_answer_shape() -> None:
    cache_store = FakeCacheStore()
    config = default_config()
    pricing = default_pricing()

    response_json, meta = exa_answer(
        "What is the Florida appraisal clause dispute process?",
        config=config,
        pricing=pricing,
        exa_api_key="",
        smoke_no_network=True,
        run_id="answer-run",
        cache_store=cache_store,
    )

    assert response_json["answer"].startswith("Mock answer for query:")
    assert len(response_json["citations"]) == 2
    assert meta.cache_hit is False
    assert meta.request_payload == {"query": "What is the Florida appraisal clause dispute process?", "text": True}
    assert meta.estimated_cost_usd == pricing["search_1_25"]
    assert cache_store.calls[0]["run_id"] == "answer-run"


def test_exa_search_people_meta_prefers_response_search_type(monkeypatch) -> None:
    cache_store = FakeCacheStore()
    config = default_config()
    pricing = default_pricing()

    def fake_http_call(payload, **_kwargs):
        return {
            "requestId": "req-modern-search-type",
            "searchType": "neural",
            "results": [],
            "costDollars": {"total": 0.0},
        }

    monkeypatch.setattr("exa_demo.client.exa_http_call", fake_http_call)

    _response_json, meta = exa_search_people(
        "insurance expert witness",
        config=config,
        pricing=pricing,
        exa_api_key="",
        smoke_no_network=True,
        run_id="search-type-run",
        cache_store=cache_store,
    )

    assert meta.resolved_search_type == "neural"


def test_exa_search_people_meta_falls_back_to_requested_type(monkeypatch) -> None:
    cache_store = FakeCacheStore()
    config = default_config()
    config["search_type"] = "deep"
    pricing = default_pricing()
    legacy_search_type_key = "resolved" + "SearchType"

    def fake_http_call(payload, **_kwargs):
        return {
            "requestId": "req-requested-search-type",
            legacy_search_type_key: "deep-reasoning",
            "results": [],
            "costDollars": {"total": 0.0},
        }

    monkeypatch.setattr("exa_demo.client.exa_http_call", fake_http_call)

    _response_json, meta = exa_search_people(
        "insurance expert witness",
        config=config,
        pricing=pricing,
        exa_api_key="",
        smoke_no_network=True,
        run_id="requested-type-run",
        cache_store=cache_store,
    )

    assert meta.request_payload["type"] == "deep"
    assert meta.resolved_search_type == "deep"


def test_exa_research_uses_smoke_report_shape() -> None:
    cache_store = FakeCacheStore()
    config = default_config()
    pricing = default_pricing()

    response_json, meta = exa_research(
        "Summarize the Florida CAT market outlook.",
        config=config,
        pricing=pricing,
        exa_api_key="",
        smoke_no_network=True,
        run_id="research-run",
        cache_store=cache_store,
    )

    assert response_json["searchType"] == "deep-reasoning"
    assert len(response_json["results"]) == 5
    assert response_json["results"][0]["title"] == "Mock Research Source 1"
    assert response_json["output"]["grounding"][0]["url"].startswith("https://example.com/mock-research/")
    assert meta.cache_hit is False
    assert meta.request_payload["query"] == "Summarize the Florida CAT market outlook."
    assert meta.request_payload["type"] == "deep-reasoning"
    assert meta.request_payload["contents"]["highlights"] == {"maxCharacters": 2666}
    assert meta.resolved_search_type == "deep-reasoning"
    assert meta.estimated_cost_usd == pricing["search_1_25"]
    assert cache_store.calls[0]["run_id"] == "research-run"
    assert_no_deprecated_request_fields(meta.request_payload)


def test_exa_research_posts_to_search_endpoint_for_live_transport(monkeypatch) -> None:
    cache_store = FakeCacheStore()
    config = default_config()
    pricing = default_pricing()
    captured = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "requestId": "req-live-research",
                "searchType": "deep-reasoning",
                "results": [
                    {
                        "title": "Florida CAT market source",
                        "url": "https://example.com/florida-cat-market",
                        "snippet": "Market conditions remain dynamic.",
                    }
                ],
                "costDollars": {"search": 0.0, "contents": 0.0, "total": 0.0},
            }

    def fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("exa_demo.client.requests.post", fake_post)

    response_json, meta = exa_research(
        "Summarize the Florida CAT market outlook.",
        config=config,
        pricing=pricing,
        exa_api_key="test-key",
        smoke_no_network=False,
        run_id="research-live-run",
        cache_store=cache_store,
    )

    assert captured["url"] == "https://api.exa.ai/search"
    assert not str(captured["url"]).endswith("/research")
    assert captured["json"]["type"] == "deep-reasoning"
    assert captured["json"]["contents"]["highlights"] == {"maxCharacters": 2666}
    assert response_json["requestId"] == "req-live-research"
    assert meta.request_id == "req-live-research"
    assert meta.resolved_search_type == "deep-reasoning"


def test_exa_structured_search_uses_smoke_structured_output_shape() -> None:
    cache_store = FakeCacheStore()
    config = default_config()
    pricing = default_pricing()
    output_schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "professionals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "role": {"type": "string"},
                    },
                },
            },
        },
    }

    response_json, meta = exa_structured_search(
        "What is the Florida appraisal clause dispute process?",
        config=config,
        pricing=pricing,
        exa_api_key="",
        smoke_no_network=True,
        run_id="structured-run",
        cache_store=cache_store,
        output_schema=output_schema,
        num_results=2,
    )

    assert response_json["structuredOutput"]["summary"].startswith("Mock summary for query:")
    assert response_json["structuredOutput"]["professionals"][0]["name"].startswith("Mock name for query:")
    assert meta.cache_hit is False
    assert meta.request_payload["outputSchema"] == output_schema
    assert meta.estimated_cost_usd == cache_store.calls[0]["estimated_cost"]
    assert cache_store.calls[0]["run_id"] == "structured-run"


def test_exa_find_similar_uses_smoke_similar_shape() -> None:
    cache_store = FakeCacheStore()
    config = default_config()
    pricing = default_pricing()

    response_json, meta = exa_find_similar(
        "https://example.com/article",
        config=config,
        pricing=pricing,
        exa_api_key="",
        smoke_no_network=True,
        run_id="similar-run",
        cache_store=cache_store,
        exclude_source_domain=True,
        text=True,
        highlights=True,
        context=True,
        num_results=2,
    )

    assert response_json["context"].startswith("Mock context for seed URL https://example.com/article")
    assert response_json["results"][0]["text"].startswith("Mock similar text for seed URL:")
    assert meta.cache_hit is False
    assert meta.request_payload["url"] == "https://example.com/article"
    assert meta.request_payload["excludeSourceDomain"] is True
    assert meta.request_payload["contents"]["text"] is True
    assert meta.request_payload["contents"]["highlights"] == {"maxCharacters": 2666}
    assert meta.request_payload["contents"]["context"] is True
    assert meta.estimated_cost_usd == cache_store.calls[0]["estimated_cost"]
    assert cache_store.calls[0]["run_id"] == "similar-run"
    assert_no_deprecated_request_fields(meta.request_payload)
