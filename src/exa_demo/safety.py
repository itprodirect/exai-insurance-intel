from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(\+?\d[\d\-\s().]{7,}\d)")
STREETISH_RE = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9.\-]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Way)\b",
    re.IGNORECASE,
)


def redact_text(text: Optional[str], *, enabled: bool = True) -> Optional[str]:
    if not text or not enabled:
        return text
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = STREETISH_RE.sub("[REDACTED_ADDRESS]", text)
    return text


_RESULT_TEXT_FIELDS = ("text", "summary", "title", "author")


def redact_response(response_json: Dict[str, Any], *, enabled: bool = True) -> Dict[str, Any]:
    """Redact PII from an Exa API response *before* it reaches the cache.

    Operates on a shallow copy so the caller's original dict is not mutated.
    Only touches fields that may carry free-text PII; structural fields
    (url, id, score, costDollars, …) are left intact.
    """
    if not enabled or not isinstance(response_json, dict):
        return response_json

    out = dict(response_json)
    results = out.get("results")
    if isinstance(results, list):
        redacted_results = []
        for item in results:
            if not isinstance(item, dict):
                redacted_results.append(item)
                continue
            item = dict(item)  # shallow copy
            for field in _RESULT_TEXT_FIELDS:
                val = item.get(field)
                if isinstance(val, str):
                    item[field] = redact_text(val)
            highlights = item.get("highlights")
            if isinstance(highlights, list):
                item["highlights"] = [
                    redact_text(h) if isinstance(h, str) else h
                    for h in highlights
                ]
            redacted_results.append(item)
        out["results"] = redacted_results

    # answer / research endpoints store top-level "answer" text
    if isinstance(out.get("answer"), str):
        out["answer"] = redact_text(out["answer"])

    return out


def extract_preview(
    result: Mapping[str, Any],
    max_chars: int = 280,
    *,
    redact_enabled: bool = True,
) -> str:
    highlights = result.get("highlights")
    if isinstance(highlights, list) and highlights:
        return redact_text(" | ".join(str(x) for x in highlights), enabled=redact_enabled) or ""

    text = result.get("text")
    if isinstance(text, str) and text:
        return redact_text(text[:max_chars], enabled=redact_enabled) or ""

    summary = result.get("summary")
    if isinstance(summary, str):
        return redact_text(summary[:max_chars], enabled=redact_enabled) or ""

    return ""