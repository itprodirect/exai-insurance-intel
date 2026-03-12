from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence
from urllib.parse import urlparse

import pandas as pd

from .models import QueryEvaluationRecord


DEFAULT_RELEVANCE_KEYWORDS: List[str] = [
    "expert witness",
    "forensic",
    "insurance",
    "appraisal",
    "adjuster",
    "coverage",
    "litigation",
    "catastrophe",
]

FAILURE_NO_RESULTS = "no_results"
FAILURE_OFF_DOMAIN = "off_domain"
FAILURE_LOW_CONFIDENCE = "low_confidence"

OFF_DOMAIN_RELEVANCE_THRESHOLD = 0.25
LOW_CONFIDENCE_THRESHOLD = 0.50
MIN_ACTIONABLE_PREVIEW_CHARS = 40

DEFAULT_BENCHMARK_PATH = Path(__file__).resolve().parents[2] / "benchmarks" / "insurance_cat_queries.json"


def load_benchmark_queries(path: str | Path | None = None) -> List[str]:
    benchmark_path = Path(path) if path is not None else DEFAULT_BENCHMARK_PATH
    with benchmark_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, list) or not all(isinstance(item, str) and item.strip() for item in data):
        raise ValueError(f"Benchmark query file must be a JSON array of non-empty strings: {benchmark_path}")

    return [item.strip() for item in data]


def evaluate_result_set(
    results: Sequence[Mapping[str, Any]],
    *,
    num_results: int,
    relevance_keywords: Iterable[str],
    redact_text: Callable[[Optional[str]], Optional[str]],
    extract_preview: Callable[[Mapping[str, Any], int], str],
    preview_chars: int = 220,
) -> Dict[str, Any]:
    top_n = list(results[: int(num_results)])
    top = top_n[0] if top_n else {}
    linkedin_present = any("linkedin.com" in str(row.get("url") or "").lower() for row in top_n)

    normalized_keywords = [str(keyword).strip().lower() for keyword in relevance_keywords if str(keyword).strip()]
    relevance_signal_rows = 0
    credibility_signal_rows = 0
    actionable_signal_rows = 0

    for row in top_n:
        row_domain = _url_domain(row.get("url"))
        highlights = row.get("highlights")
        text = row.get("text")

        parts = [str(row.get("title") or "")]
        if isinstance(highlights, list):
            parts.extend(str(item) for item in highlights)
        if isinstance(text, str):
            parts.append(text[:200])

        blob = " ".join(parts).lower()
        has_relevance_signal = any(keyword in blob for keyword in normalized_keywords)
        if has_relevance_signal:
            relevance_signal_rows += 1

        has_url = bool(str(row.get("url") or "").strip())
        has_content = bool(str(row.get("title") or "").strip()) or bool(highlights) or bool(str(text or "").strip())
        if has_url and has_content and row_domain:
            credibility_signal_rows += 1

        preview = extract_preview(row, preview_chars) if isinstance(row, Mapping) else ""
        if has_url and len(str(preview or "").strip()) >= MIN_ACTIONABLE_PREVIEW_CHARS:
            actionable_signal_rows += 1

    top_n_count = len(top_n)
    relevance_score = (relevance_signal_rows / top_n_count) if top_n_count else 0.0
    credibility_score = (credibility_signal_rows / top_n_count) if top_n_count else 0.0
    actionability_score = (actionable_signal_rows / top_n_count) if top_n_count else 0.0
    confidence_score = (0.5 * relevance_score) + (0.3 * credibility_score) + (0.2 * actionability_score)

    failure_reasons: List[str] = []
    if len(results) == 0:
        failure_reasons.append(FAILURE_NO_RESULTS)
    else:
        if relevance_score < OFF_DOMAIN_RELEVANCE_THRESHOLD:
            failure_reasons.append(FAILURE_OFF_DOMAIN)
        if confidence_score < LOW_CONFIDENCE_THRESHOLD:
            failure_reasons.append(FAILURE_LOW_CONFIDENCE)

    primary_failure_reason = failure_reasons[0] if failure_reasons else None
    relevance_keywords_present = relevance_score > 0.0

    return {
        "top_title": redact_text(top.get("title")) if isinstance(top, Mapping) else None,
        "top_url": top.get("url") if isinstance(top, Mapping) else None,
        "top_preview": extract_preview(top, preview_chars) if isinstance(top, Mapping) else "",
        "linkedin_present": linkedin_present,
        "relevance_keywords_present": relevance_keywords_present,
        "relevance_score": round(relevance_score, 6),
        "credibility_score": round(credibility_score, 6),
        "actionability_score": round(actionability_score, 6),
        "confidence_score": round(confidence_score, 6),
        "failure_reasons": failure_reasons,
        "primary_failure_reason": primary_failure_reason,
        "result_count": len(results),
    }


def evaluate_batch_queries(
    queries: Sequence[str],
    *,
    search_people: Callable[..., Any],
    num_results: int,
    relevance_keywords: Optional[Sequence[str]] = None,
    redact_text: Callable[[Optional[str]], Optional[str]],
    extract_preview: Callable[[Mapping[str, Any], int], str],
    record_query: Optional[Callable[[QueryEvaluationRecord], None]] = None,
) -> pd.DataFrame:
    keywords = list(relevance_keywords or DEFAULT_RELEVANCE_KEYWORDS)
    batch_rows: List[Dict[str, Any]] = []

    for query in queries:
        response_json, meta = search_people(query, num_results=num_results)
        results = response_json.get("results", []) if isinstance(response_json, dict) else []
        evaluated = evaluate_result_set(
            results,
            num_results=num_results,
            relevance_keywords=keywords,
            redact_text=redact_text,
            extract_preview=extract_preview,
        )
        record = QueryEvaluationRecord.from_runtime(query, response_json, meta, evaluated)
        if record_query is not None:
            record_query(record)
        batch_rows.append(record.to_flat_dict())

    return pd.DataFrame(batch_rows)


def _url_domain(url: Any) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    try:
        parsed = urlparse(text)
    except ValueError:
        return ""
    return str(parsed.netloc or "").lower()
