from __future__ import annotations

from exa_demo.safety import extract_preview, redact_text


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