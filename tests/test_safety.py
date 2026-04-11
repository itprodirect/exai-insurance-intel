from __future__ import annotations

from exa_demo.safety import extract_preview, redact_response, redact_text


def test_redact_text_removes_email_phone_and_address() -> None:
    text = "Reach me at analyst@example.com or +1 (555) 123-4567 near 123 Main Street."
    redacted = redact_text(text)

    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_ADDRESS]" in redacted


def test_extract_preview_prefers_highlights_and_redacts() -> None:
    result = {
        "highlights": ["Contact witness@example.com at 555-555-5555."],
        "text": "fallback text",
    }

    preview = extract_preview(result, max_chars=50)

    assert preview.startswith("Contact [REDACTED_EMAIL]")
    assert "[REDACTED_PHONE]" in preview


# ── redact_response tests ──────────────────────────────────────────


def _sample_response() -> dict:
    return {
        "requestId": "req-123",
        "resolvedSearchType": "neural",
        "results": [
            {
                "id": "r1",
                "title": "Call analyst@example.com for details",
                "url": "https://linkedin.com/in/foo",
                "text": "Reach +1 (555) 123-4567 at 123 Main Street.",
                "highlights": [
                    "Email witness@example.com for follow-up.",
                    "Public profile snippet.",
                ],
                "summary": "Contact info@claims.com to begin.",
                "author": "Jane Doe analyst@corp.com",
                "score": 0.95,
            },
        ],
        "costDollars": {"search": 0.01, "contents": 0.02, "total": 0.03},
    }


def test_redact_response_redacts_text_fields_in_results() -> None:
    resp = redact_response(_sample_response())

    result = resp["results"][0]
    assert "[REDACTED_EMAIL]" in result["title"]
    assert "analyst@example.com" not in result["title"]
    assert "[REDACTED_PHONE]" in result["text"]
    assert "[REDACTED_ADDRESS]" in result["text"]
    assert "[REDACTED_EMAIL]" in result["highlights"][0]
    assert "Public profile snippet." == result["highlights"][1]  # no PII, unchanged
    assert "[REDACTED_EMAIL]" in result["summary"]
    assert "[REDACTED_EMAIL]" in result["author"]


def test_redact_response_preserves_structural_fields() -> None:
    resp = redact_response(_sample_response())

    assert resp["requestId"] == "req-123"
    assert resp["costDollars"]["total"] == 0.03
    result = resp["results"][0]
    assert result["id"] == "r1"
    assert result["url"] == "https://linkedin.com/in/foo"
    assert result["score"] == 0.95


def test_redact_response_does_not_mutate_original() -> None:
    original = _sample_response()
    original_title = original["results"][0]["title"]
    redact_response(original)
    assert original["results"][0]["title"] == original_title


def test_redact_response_disabled_returns_unchanged() -> None:
    original = _sample_response()
    resp = redact_response(original, enabled=False)
    assert resp is original


def test_redact_response_handles_answer_field() -> None:
    resp = redact_response({
        "requestId": "a1",
        "answer": "Contact expert@claims.com for info.",
        "results": [],
    })
    assert "[REDACTED_EMAIL]" in resp["answer"]
    assert "expert@claims.com" not in resp["answer"]


def test_redact_response_handles_empty_results() -> None:
    resp = redact_response({"requestId": "r1", "results": []})
    assert resp["results"] == []


def test_redact_response_handles_missing_results_key() -> None:
    resp = redact_response({"requestId": "r1"})
    assert resp == {"requestId": "r1"}