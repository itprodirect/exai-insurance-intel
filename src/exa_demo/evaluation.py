from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

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

    relevance_text: List[str] = []
    for row in top_n:
        parts = [str(row.get("title") or "")]
        highlights = row.get("highlights")
        if isinstance(highlights, list):
            parts.extend(str(item) for item in highlights)
        text = row.get("text")
        if isinstance(text, str):
            parts.append(text[:200])
        relevance_text.append(" ".join(parts).lower())

    relevance_keywords_present = any(
        any(keyword in blob for keyword in relevance_keywords)
        for blob in relevance_text
    )

    return {
        "top_title": redact_text(top.get("title")) if isinstance(top, Mapping) else None,
        "top_url": top.get("url") if isinstance(top, Mapping) else None,
        "top_preview": extract_preview(top, preview_chars) if isinstance(top, Mapping) else "",
        "linkedin_present": linkedin_present,
        "relevance_keywords_present": relevance_keywords_present,
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
