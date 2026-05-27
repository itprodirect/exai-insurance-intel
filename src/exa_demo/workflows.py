from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping


def build_find_similar_artifact(
    seed_url: str,
    *,
    request_payload: Mapping[str, Any],
    response_json: Mapping[str, Any],
    cache_hit: bool,
    estimated_cost_usd: float,
) -> Dict[str, Any]:
    results = _normalize_find_similar_results(response_json.get("results"))
    payload = {
        "seed_url": seed_url,
        "result_count": len(results),
        "results": results,
        "top_result": results[0] if results else None,
    }
    return {
        **_artifact_base(
            request_payload=request_payload,
            response_json=response_json,
            cache_hit=cache_hit,
            estimated_cost_usd=estimated_cost_usd,
            actual_cost_usd=find_similar_actual_cost(response_json),
        ),
        **payload,
    }


def build_research_artifact(
    query: str,
    *,
    request_payload: Mapping[str, Any],
    response_json: Mapping[str, Any],
    cache_hit: bool,
    estimated_cost_usd: float,
) -> Dict[str, Any]:
    report_text = _extract_research_report_text(response_json)
    output_content = _extract_output_content(response_json)
    grounding = _extract_output_grounding(response_json)
    citations = _normalize_citations(
        response_json.get("citations")
        if isinstance(response_json.get("citations"), list)
        else response_json.get("sources")
        if isinstance(response_json.get("sources"), list)
        else response_json.get("results")
    )
    payload = {
        "query": query,
        "report_text": report_text,
        "report_preview": report_text[:220],
        "citation_count": len(citations),
        "citations": citations,
        "grounding_count": len(grounding),
    }
    if output_content is not None:
        payload["output_content"] = output_content
    if grounding:
        payload["grounding"] = grounding
    return {
        **_artifact_base(
            request_payload=request_payload,
            response_json=response_json,
            cache_hit=cache_hit,
            estimated_cost_usd=estimated_cost_usd,
            actual_cost_usd=research_actual_cost(response_json),
        ),
        **payload,
    }


def build_answer_artifact(
    query: str,
    *,
    request_payload: Mapping[str, Any],
    response_json: Mapping[str, Any],
    cache_hit: bool,
    estimated_cost_usd: float,
) -> Dict[str, Any]:
    answer_text = str(response_json.get("answer") or response_json.get("text") or "").strip()
    citations = _normalize_citations(response_json.get("citations"))
    payload = {
        "query": query,
        "answer_text": answer_text,
        "citation_count": len(citations),
        "citations": citations,
    }
    return {
        **_artifact_base(
            request_payload=request_payload,
            response_json=response_json,
            cache_hit=cache_hit,
            estimated_cost_usd=estimated_cost_usd,
            actual_cost_usd=answer_actual_cost(response_json),
        ),
        **payload,
    }


def build_structured_search_artifact(
    query: str,
    *,
    schema_path: Path,
    request_payload: Mapping[str, Any],
    response_json: Mapping[str, Any],
    cache_hit: bool,
    estimated_cost_usd: float,
) -> Dict[str, Any]:
    structured_output = _extract_structured_output(response_json)
    output_content = _extract_output_content(response_json)
    grounding = _extract_output_grounding(response_json)
    payload = {
        "query": query,
        "schema_file": str(schema_path),
        "structured_output": structured_output,
        "structured_output_keys": sorted(structured_output.keys()) if isinstance(structured_output, Mapping) else [],
        "grounding_count": len(grounding),
    }
    if output_content is not None:
        payload["output_content"] = output_content
    if grounding:
        payload["grounding"] = grounding
    return {
        **_artifact_base(
            request_payload=request_payload,
            response_json=response_json,
            cache_hit=cache_hit,
            estimated_cost_usd=estimated_cost_usd,
            actual_cost_usd=structured_search_actual_cost(response_json),
        ),
        **payload,
    }


def _normalize_citations(value: Any) -> list[Dict[str, Any]]:
    if not isinstance(value, list):
        return []

    citations: list[Dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        citations.append(
            {
                "title": str(item.get("title") or item.get("name") or "").strip(),
                "url": str(item.get("url") or item.get("sourceUrl") or "").strip(),
                "snippet": _citation_snippet(item),
            }
        )
    return citations


def _normalize_find_similar_results(value: Any) -> list[Dict[str, Any]]:
    if not isinstance(value, list):
        return []

    results: list[Dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        results.append(
            {
                "title": str(item.get("title") or "").strip(),
                "url": str(item.get("url") or "").strip(),
                "snippet": str(item.get("snippet") or item.get("text") or "").strip(),
                "score": _coerce_optional_float(item.get("score")),
            }
        )
    return results


def answer_actual_cost(response_json: Mapping[str, Any]) -> float:
    return _answer_actual_cost(response_json)


def research_actual_cost(response_json: Mapping[str, Any]) -> float:
    return _answer_actual_cost(response_json)


def structured_search_actual_cost(response_json: Mapping[str, Any]) -> float:
    return _answer_actual_cost(response_json)


def find_similar_actual_cost(response_json: Mapping[str, Any]) -> float:
    return _answer_actual_cost(response_json)


def _answer_actual_cost(response_json: Mapping[str, Any]) -> float:
    cost = response_json.get("costDollars")
    if isinstance(cost, Mapping):
        total = cost.get("total")
        try:
            return float(total)
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _extract_structured_output(response_json: Mapping[str, Any]) -> Any:
    if not isinstance(response_json, Mapping):
        return None

    for key in ("structuredData", "structuredOutput", "output", "data"):
        value = response_json.get(key)
        if key == "output" and isinstance(value, Mapping) and "content" in value:
            value = value.get("content")
        if value is not None:
            return value

    results = response_json.get("results")
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, Mapping):
                continue
            for key in ("structuredData", "structuredOutput", "output", "data"):
                value = item.get(key)
                if key == "output" and isinstance(value, Mapping) and "content" in value:
                    value = value.get("content")
                if value is not None:
                    return value
    return None


def _extract_research_report_text(response_json: Mapping[str, Any]) -> str:
    if not isinstance(response_json, Mapping):
        return ""

    for key in ("report", "reportText", "markdown", "summary", "text", "response", "content"):
        value = response_json.get(key)
        if value is not None:
            return str(value).strip()
    output_text = _output_content_text(response_json)
    if output_text:
        return output_text
    return _render_research_report_from_results(response_json.get("results"))


def _render_research_report_from_results(value: Any) -> str:
    if not isinstance(value, list):
        return ""

    source_lines: list[str] = []
    for index, item in enumerate(value[:5], start=1):
        if not isinstance(item, Mapping):
            continue
        title = str(item.get("title") or f"Source {index}").strip()
        snippet = _citation_snippet(item)
        if snippet:
            source_lines.append(f"{index}. {title}: {snippet}")
        else:
            source_lines.append(f"{index}. {title}")

    if not source_lines:
        return ""

    return "\n".join(
        [
            "Search-backed research report.",
            "",
            "Key source signals:",
            *source_lines,
            "",
            "Human review is required before operational use.",
        ]
    )


def _citation_snippet(item: Mapping[str, Any]) -> str:
    for key in ("snippet", "summary", "text", "passage"):
        value = item.get(key)
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    highlights = item.get("highlights")
    if isinstance(highlights, list):
        for highlight in highlights:
            text = str(highlight).strip()
            if text:
                return text
    return ""


def _output_content_text(response_json: Mapping[str, Any]) -> str:
    output = response_json.get("output")
    if not isinstance(output, Mapping):
        return ""
    content = output.get("content")
    if isinstance(content, (str, int, float, bool)):
        return str(content).strip()
    return ""


def _extract_output_content(response_json: Mapping[str, Any]) -> Any | None:
    if not isinstance(response_json, Mapping):
        return None

    output = response_json.get("output")
    if not isinstance(output, Mapping) or "content" not in output:
        return None

    content = output.get("content")
    if content is None:
        return None
    return _jsonable_value(content)


def _extract_output_grounding(response_json: Mapping[str, Any]) -> list[Dict[str, Any]]:
    if not isinstance(response_json, Mapping):
        return []

    output = response_json.get("output")
    if not isinstance(output, Mapping):
        return []

    return _normalize_grounding(output.get("grounding"))


def _normalize_grounding(value: Any) -> list[Dict[str, Any]]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, Mapping):
        raw_items = [value]
    else:
        return []

    grounding: list[Dict[str, Any]] = []
    for item in raw_items:
        normalized = _normalize_grounding_item(item)
        if normalized:
            grounding.append(normalized)
    return grounding


def _normalize_grounding_item(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        source = value.get("source")
        source_mapping = source if isinstance(source, Mapping) else {}
        title = _first_clean_string(value, "title", "name", "sourceTitle")
        if not title and source_mapping:
            title = _first_clean_string(source_mapping, "title", "name", "sourceTitle")

        url = _first_clean_string(value, "url", "sourceUrl", "uri")
        if not url and source_mapping:
            url = _first_clean_string(source_mapping, "url", "sourceUrl", "uri")

        snippet = _first_clean_string(value, "snippet", "summary", "text", "quote", "passage")
        if not snippet and source_mapping:
            snippet = _first_clean_string(
                source_mapping,
                "snippet",
                "summary",
                "text",
                "quote",
                "passage",
            )

        item: Dict[str, Any] = {}
        if title:
            item["title"] = title
        if url:
            item["url"] = url
        if snippet:
            item["snippet"] = snippet
        return item

    if isinstance(value, (str, int, float, bool)):
        text = _clean_string(value)
        if text:
            return {"snippet": text}
    return {}


def load_json_schema(schema_path: Path) -> Dict[str, Any]:
    schema_text = schema_path.read_text(encoding="utf-8")
    schema = json.loads(schema_text)
    if not isinstance(schema, Mapping):
        raise ValueError(f"Schema file must contain a JSON object: {schema_path}")
    return dict(schema)


def _artifact_base(
    *,
    request_payload: Mapping[str, Any],
    response_json: Mapping[str, Any],
    cache_hit: bool,
    estimated_cost_usd: float,
    actual_cost_usd: float,
) -> Dict[str, Any]:
    return {
        "request_payload": _jsonable_mapping(request_payload),
        "response": _jsonable_mapping(response_json),
        "request_id": _request_id(response_json),
        "cache_hit": cache_hit,
        "estimated_cost_usd": float(estimated_cost_usd),
        "actual_cost_usd": float(actual_cost_usd),
    }


def _jsonable_mapping(value: Mapping[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(dict(value), ensure_ascii=False, default=str))


def _jsonable_value(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _request_id(response_json: Mapping[str, Any]) -> str | None:
    if not isinstance(response_json, Mapping):
        return None
    value = response_json.get("requestId")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _first_clean_string(mapping: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        text = _clean_string(mapping.get(key))
        if text:
            return text
    return ""
