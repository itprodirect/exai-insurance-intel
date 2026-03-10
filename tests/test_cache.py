from __future__ import annotations

from exa_demo.cache import request_hash_for_payload


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