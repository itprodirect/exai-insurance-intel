from __future__ import annotations

from exa_demo.client import build_exa_payload, mock_exa_response
from exa_demo.config import default_config


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
            "livecrawl": True,
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
    assert payload["livecrawl"] is True
    assert "results" not in payload


def test_build_exa_payload_leaves_additive_fields_out_by_default() -> None:
    config = default_config()

    payload = build_exa_payload("insurance expert witness", config)

    assert "additionalQueries" not in payload
    assert "startPublishedDate" not in payload
    assert "endPublishedDate" not in payload
    assert "livecrawl" not in payload


def test_mock_exa_response_preserves_search_result_shape_with_additive_controls() -> None:
    payload = build_exa_payload(
        "insurance expert witness",
        {
            **default_config(),
            "additional_queries": ["licensed public adjuster Florida"],
            "start_published_date": "2026-01-01",
            "end_published_date": "2026-03-01",
            "livecrawl": True,
        },
    )

    response = mock_exa_response(payload)

    assert response["resolvedSearchType"] == "auto"
    assert isinstance(response["results"], list)
    assert len(response["results"]) == payload["numResults"]
    assert response["results"][0]["title"].startswith("Mock Professional Result")
