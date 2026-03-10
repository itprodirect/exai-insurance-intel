from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Mapping


DEFAULT_CONFIG: Dict[str, Any] = {
    "exa_endpoint": "https://api.exa.ai/search",
    "search_type": "auto",
    "category": "people",
    "num_results": 5,
    "user_location": "US",
    "use_text": False,
    "use_highlights": True,
    "highlights_per_url": 1,
    "highlight_num_sentences": 2,
    "use_summary": False,
    "include_domains": [],
    "exclude_domains": [],
    "moderation": True,
    "redact_emails_phones": True,
    "budget_cap_usd": 7.50,
    "sqlite_path": "exa_cache.sqlite",
    "cache_ttl_hours": 24 * 30,
    "max_supported_results_for_estimate": 100,
}

DEFAULT_PRICING: Dict[str, float] = {
    "search_1_25": 0.005,
    "search_26_100": 0.025,
    "content_text_per_page": 0.001,
    "content_highlights_per_page": 0.001,
    "content_summary_per_page": 0.001,
}


@dataclass(frozen=True)
class RuntimeState:
    exa_api_key: str
    smoke_no_network: bool
    run_id: str


def default_config() -> Dict[str, Any]:
    return deepcopy(DEFAULT_CONFIG)


def default_pricing() -> Dict[str, float]:
    return deepcopy(DEFAULT_PRICING)


def load_runtime_state(
    *,
    env: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> RuntimeState:
    env = env or os.environ
    now = now or datetime.now(timezone.utc)

    exa_api_key = (env.get("EXA_API_KEY") or "").strip()
    smoke_no_network = (env.get("EXA_SMOKE_NO_NETWORK") or "0").strip() == "1"
    run_id = (env.get("EXA_RUN_ID") or now.strftime("%Y%m%dT%H%M%SZ")).strip()

    if not exa_api_key and not smoke_no_network:
        raise RuntimeError(
            "Missing EXA_API_KEY. Create .env from .env.example and set EXA_API_KEY=...\n"
            "For local smoke runs (no network/API billing), set EXA_SMOKE_NO_NETWORK=1."
        )

    return RuntimeState(
        exa_api_key=exa_api_key,
        smoke_no_network=smoke_no_network,
        run_id=run_id,
    )