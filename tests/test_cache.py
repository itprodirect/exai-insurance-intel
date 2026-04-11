from __future__ import annotations

import json
import tempfile
from pathlib import Path

from exa_demo.cache import SqliteCacheStore, request_hash_for_payload


def test_request_hash_is_deterministic_across_key_order() -> None:
    payload_a = {
        "query": "forensic engineer",
        "numResults": 5,
        "contents": {"highlights": {"numSentences": 2, "highlightsPerUrl": 1}},
    }
    payload_b = {
        "contents": {"highlights": {"highlightsPerUrl": 1, "numSentences": 2}},
        "numResults": 5,
        "query": "forensic engineer",
    }

    assert request_hash_for_payload(payload_a) == request_hash_for_payload(payload_b)


def test_get_or_set_applies_response_filter_before_caching() -> None:
    """Verify that response_filter transforms the response before it is persisted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = SqliteCacheStore(db_path, cache_ttl_hours=1.0)

        payload = {"query": "test filter", "numResults": 1}
        raw_response = {
            "requestId": "rf-1",
            "results": [
                {
                    "id": "r1",
                    "title": "Contact analyst@example.com",
                    "highlights": ["Email witness@example.com"],
                }
            ],
            "costDollars": {"total": 0.01},
        }

        def _filter(resp: dict) -> dict:
            """Replace emails with [FILTERED]."""
            import re

            text = json.dumps(resp)
            text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", "[FILTERED]", text)
            return json.loads(text)

        result, cache_hit = store.get_or_set(
            payload,
            estimated_cost=0.01,
            run_id="run-filter-test",
            budget_cap_usd=10.0,
            fetcher=lambda _p: raw_response,
            response_filter=_filter,
        )

        # Returned value should be filtered
        assert cache_hit is False
        assert "[FILTERED]" in result["results"][0]["title"]
        assert "analyst@example.com" not in result["results"][0]["title"]

        # Cached value should also be filtered (lookup returns filtered data)
        cached_result, cache_hit2 = store.get_or_set(
            payload,
            estimated_cost=0.01,
            run_id="run-filter-test",
            budget_cap_usd=10.0,
            fetcher=lambda _p: (_ for _ in ()).throw(AssertionError("should not call fetcher")),
            response_filter=_filter,
        )
        assert cache_hit2 is True
        assert "[FILTERED]" in cached_result["results"][0]["title"]
        assert "analyst@example.com" not in cached_result["results"][0]["title"]