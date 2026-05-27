from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

from .config import DEFAULT_HIGHLIGHT_MAX_CHARACTERS


def build_exa_payload(
    query: str,
    config: Mapping[str, Any],
    *,
    num_results: Optional[int] = None,
) -> Dict[str, Any]:
    resolved_num_results = int(num_results or config["num_results"])
    payload: Dict[str, Any] = {
        "query": query,
        "type": config["search_type"],
        "category": config["category"],
        "numResults": resolved_num_results,
        "userLocation": config["user_location"],
        "moderation": config["moderation"],
    }

    if config["include_domains"]:
        payload["includeDomains"] = config["include_domains"]
    if config["exclude_domains"]:
        payload["excludeDomains"] = config["exclude_domains"]
    additional_queries = _clean_string_list(config.get("additional_queries"))
    if additional_queries:
        payload["additionalQueries"] = additional_queries
    _assign_text_field(payload, "startPublishedDate", config.get("start_published_date"))
    _assign_text_field(payload, "endPublishedDate", config.get("end_published_date"))

    contents: Dict[str, Any] = {}
    if config["use_text"]:
        contents["text"] = True
    if config["use_highlights"]:
        contents["highlights"] = _highlight_options(config)
    if config["use_summary"]:
        contents["summary"] = {
            "query": "Summarize the person's professional background and insurance/CAT relevance."
        }
    _assign_int_field(contents, "maxAgeHours", config.get("max_age_hours"))
    _assign_int_field(contents, "livecrawlTimeout", config.get("livecrawl_timeout"))

    if contents:
        payload["contents"] = contents

    return payload


def build_answer_payload(query: str) -> Dict[str, Any]:
    return {"query": query, "text": True}


def build_research_payload(
    query: str,
    config: Mapping[str, Any],
    *,
    num_results: Optional[int] = None,
) -> Dict[str, Any]:
    research_config = dict(config)
    research_config["search_type"] = "deep-reasoning"
    return build_exa_payload(query, research_config, num_results=num_results)


def build_structured_search_payload(
    query: str,
    config: Mapping[str, Any],
    output_schema: Mapping[str, Any],
    *,
    num_results: Optional[int] = None,
) -> Dict[str, Any]:
    payload = build_exa_payload(query, config, num_results=num_results)
    payload["outputSchema"] = dict(output_schema)
    return payload


def build_find_similar_payload(
    url: str,
    config: Mapping[str, Any],
    *,
    num_results: Optional[int] = None,
    include_domains: Optional[Sequence[str]] = None,
    exclude_domains: Optional[Sequence[str]] = None,
    start_crawl_date: Optional[str] = None,
    end_crawl_date: Optional[str] = None,
    start_published_date: Optional[str] = None,
    end_published_date: Optional[str] = None,
    exclude_source_domain: Optional[bool] = None,
    category: Optional[str] = None,
    text: Any = None,
    highlights: Any = None,
    context: Any = None,
    moderation: Optional[bool] = None,
) -> Dict[str, Any]:
    resolved_num_results = int(num_results or config["num_results"])
    payload: Dict[str, Any] = {
        "url": url,
        "numResults": resolved_num_results,
        "category": str(category or config["category"]),
        "moderation": bool(config["moderation"] if moderation is None else moderation),
    }

    resolved_include_domains = _clean_string_list(
        include_domains if include_domains is not None else config["include_domains"]
    )
    if resolved_include_domains:
        payload["includeDomains"] = resolved_include_domains

    resolved_exclude_domains = _clean_string_list(
        exclude_domains if exclude_domains is not None else config["exclude_domains"]
    )
    if resolved_exclude_domains:
        payload["excludeDomains"] = resolved_exclude_domains

    _assign_text_field(payload, "startCrawlDate", start_crawl_date)
    _assign_text_field(payload, "endCrawlDate", end_crawl_date)
    _assign_text_field(payload, "startPublishedDate", start_published_date)
    _assign_text_field(payload, "endPublishedDate", end_published_date)
    if exclude_source_domain is not None:
        payload["excludeSourceDomain"] = bool(exclude_source_domain)

    contents: Dict[str, Any] = {}
    resolved_text = True if text is None else text
    if resolved_text is not None:
        contents["text"] = resolved_text
    if highlights is not None:
        contents["highlights"] = _normalize_highlights(highlights, config)
    if context is not None:
        contents["context"] = context
    _assign_int_field(contents, "maxAgeHours", config.get("max_age_hours"))
    _assign_int_field(contents, "livecrawlTimeout", config.get("livecrawl_timeout"))
    if contents:
        payload["contents"] = contents

    return payload


def _clean_string_list(values: Any) -> list[str]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return []
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text:
            result.append(text)
    return result


def _assign_text_field(payload: Dict[str, Any], field_name: str, value: Any) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text:
        payload[field_name] = text


def _assign_int_field(payload: Dict[str, Any], field_name: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str) and not value.strip():
        return
    payload[field_name] = int(value)


def _highlight_options(config: Mapping[str, Any]) -> Dict[str, int]:
    return {
        "maxCharacters": int(
            config.get("highlight_max_characters") or DEFAULT_HIGHLIGHT_MAX_CHARACTERS
        )
    }


def _normalize_highlights(highlights: Any, config: Mapping[str, Any]) -> Any:
    if highlights is True:
        return _highlight_options(config)
    if not isinstance(highlights, Mapping):
        return highlights

    if "maxCharacters" in highlights:
        value = highlights["maxCharacters"]
    elif "max_characters" in highlights:
        value = highlights["max_characters"]
    elif "numSentences" in highlights:
        value = int(highlights["numSentences"]) * 1333
    else:
        value = config.get("highlight_max_characters") or DEFAULT_HIGHLIGHT_MAX_CHARACTERS

    normalized = {
        str(key): item
        for key, item in highlights.items()
        if str(key) not in {"highlightsPerUrl", "numSentences", "max_characters"}
    }
    normalized["maxCharacters"] = int(value)
    return normalized
