from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, Optional, Sequence

from dotenv import load_dotenv

from .cache import SqliteCacheStore
from .cli_parser import (
    apply_search_overrides as _apply_search_overrides,
    build_parser as build_cli_parser,
    namespace_with_overrides as _namespace_with_overrides,
    run_id_suffix_for_search_type as _run_id_suffix_for_search_type,
)
from .config import RuntimeState, default_config, default_pricing, load_runtime_state
from .endpoint_workflows import (
    emit_answer_payload,
    emit_find_similar_payload,
    emit_research_payload,
    emit_structured_search_payload,
    run_answer_workflow,
    run_find_similar_workflow,
    run_research_workflow,
    run_structured_search_workflow,
)
from .ranked_workflows import emit_eval_payload, emit_search_payload, normalized_query_suite, run_eval_workflow as run_ranked_eval_workflow, run_search_workflow


def build_parser() -> argparse.ArgumentParser:
    return build_cli_parser(
        handlers={
            "search": run_search_command,
            "eval": run_eval_command,
            "answer": run_answer_command,
            "research": run_research_command,
            "find-similar": run_find_similar_command,
            "structured-search": run_structured_search_command,
            "compare-search-types": run_compare_search_types_command,
            "budget": run_budget_command,
        }
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))


def run_search_command(args: argparse.Namespace) -> int:
    config, pricing, runtime = _prepare_runtime(args)
    payload, record = run_search_workflow(
        query=args.query,
        artifact_dir=args.artifact_dir,
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=_runtime_metadata(runtime),
    )
    emit_search_payload(payload, record=record, as_json=bool(args.as_json))
    return 0


def run_eval_command(args: argparse.Namespace) -> int:
    payload = _run_eval_workflow(args)
    emit_eval_payload(payload, as_json=bool(args.as_json))
    return 0


def run_answer_command(args: argparse.Namespace) -> int:
    config, pricing, runtime = _prepare_runtime(args)
    payload = run_answer_workflow(
        query=args.query,
        artifact_dir=args.artifact_dir,
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=_runtime_metadata(runtime),
    )
    emit_answer_payload(payload, as_json=bool(args.as_json))
    return 0


def run_research_command(args: argparse.Namespace) -> int:
    config, pricing, runtime = _prepare_runtime(args)
    payload = run_research_workflow(
        query=args.query,
        artifact_dir=args.artifact_dir,
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=_runtime_metadata(runtime),
    )
    emit_research_payload(payload, as_json=bool(args.as_json))
    return 0


def run_find_similar_command(args: argparse.Namespace) -> int:
    config, pricing, runtime = _prepare_runtime(args)
    payload = run_find_similar_workflow(
        seed_url=args.url,
        artifact_dir=args.artifact_dir,
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=_runtime_metadata(runtime),
    )
    emit_find_similar_payload(payload, as_json=bool(args.as_json))
    return 0


def run_structured_search_command(args: argparse.Namespace) -> int:
    config, pricing, runtime = _prepare_runtime(args)
    payload = run_structured_search_workflow(
        query=args.query,
        schema_file=args.schema_file,
        artifact_dir=args.artifact_dir,
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=_runtime_metadata(runtime),
    )
    emit_structured_search_payload(payload, as_json=bool(args.as_json))
    return 0


def run_compare_search_types_command(args: argparse.Namespace) -> int:
    baseline_type = str(args.baseline_type or "").strip()
    candidate_type = str(args.candidate_type or "").strip()
    if not baseline_type or not candidate_type:
        raise ValueError("Both --baseline-type and --candidate-type must be non-empty.")
    if baseline_type == candidate_type:
        raise ValueError("Baseline and candidate search types must differ.")

    load_dotenv()
    base_runtime = _resolve_runtime(args.mode, getattr(args, "run_id", None))
    base_run_id = base_runtime.run_id
    baseline_run_id = f"{base_run_id}-{_run_id_suffix_for_search_type(baseline_type)}"
    candidate_run_id = f"{base_run_id}-{_run_id_suffix_for_search_type(candidate_type)}"

    baseline_payload = _run_eval_workflow(
        args,
        run_id_override=baseline_run_id,
        search_type_override=baseline_type,
    )
    candidate_payload = _run_eval_workflow(
        args,
        run_id_override=candidate_run_id,
        search_type_override=candidate_type,
        compare_to_run_id=baseline_run_id,
        compare_base_dir=args.artifact_dir,
    )

    payload = {
        "workflow": "compare-search-types",
        "base_run_id": base_run_id,
        "query_suite": normalized_query_suite(getattr(args, "suite", None)),
        "baseline_search_type": baseline_type,
        "candidate_search_type": candidate_type,
        "baseline_run": baseline_payload,
        "candidate_run": candidate_payload,
        "comparison": candidate_payload.get("comparison"),
        "comparison_markdown_path": candidate_payload.get("comparison_markdown_path"),
    }

    if args.as_json:
        print(json.dumps(payload, indent=2))
        return 0

    comparison = payload.get("comparison") if isinstance(payload.get("comparison"), dict) else {}
    deltas = comparison.get("deltas") if isinstance(comparison.get("deltas"), dict) else {}
    print(f"workflow: compare-search-types")
    print(f"query_suite: {payload['query_suite']}")
    print(f"baseline_run_id: {baseline_run_id}")
    print(f"candidate_run_id: {candidate_run_id}")
    print(f"baseline_search_type: {baseline_type}")
    print(f"candidate_search_type: {candidate_type}")
    print(f"baseline_artifact_dir: {baseline_payload['artifact_dir']}")
    print(f"candidate_artifact_dir: {candidate_payload['artifact_dir']}")
    print(f"delta_observed_confidence_score: {float(deltas.get('observed_confidence_score') or 0.0):+.3f}")
    print(f"delta_observed_failure_rate: {float(deltas.get('observed_failure_rate') or 0.0):+.3f}")
    print(f"comparison_markdown: {payload.get('comparison_markdown_path')}")
    return 0


def _run_eval_workflow(
    args: argparse.Namespace,
    *,
    run_id_override: str | None = None,
    search_type_override: str | None = None,
    compare_to_run_id: str | None = None,
    compare_base_dir: str | None = None,
) -> Dict[str, Any]:
    workflow_args = _namespace_with_overrides(
        args,
        run_id=run_id_override if run_id_override is not None else getattr(args, "run_id", None),
        search_type=search_type_override if search_type_override is not None else getattr(args, "search_type", default_config()["search_type"]),
    )
    config, pricing, runtime = _prepare_runtime(workflow_args)
    resolved_compare_to_run_id = compare_to_run_id if compare_to_run_id is not None else getattr(args, "compare_to_run_id", None)
    resolved_compare_base_dir = compare_base_dir if compare_base_dir is not None else getattr(args, "compare_base_dir", None)
    return run_ranked_eval_workflow(
        artifact_dir=args.artifact_dir,
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=_runtime_metadata(runtime),
        suite=getattr(args, "suite", None),
        queries_file=getattr(args, "queries_file", None),
        limit=getattr(args, "limit", None),
        compare_to_run_id=resolved_compare_to_run_id,
        compare_base_dir=resolved_compare_base_dir,
    )


def run_budget_command(args: argparse.Namespace) -> int:
    cache_store = SqliteCacheStore(args.sqlite_path, float(args.cache_ttl_hours))
    summary = cache_store.spend_so_far(run_id=args.run_id)
    ledger_df = cache_store.ledger_summary(run_id=args.run_id)
    payload = {
        "run_id": args.run_id,
        "summary": summary,
        "ledger_rows": int(len(ledger_df.index)),
    }
    if args.as_json:
        print(json.dumps(payload, indent=2))
        return 0

    scope = args.run_id or "all runs"
    print(f"budget scope: {scope}")
    print(json.dumps(summary, indent=2))
    print(f"ledger_rows: {len(ledger_df.index)}")
    return 0


def _prepare_runtime(args: argparse.Namespace) -> tuple[Dict[str, Any], Dict[str, float], RuntimeState]:
    load_dotenv()
    config = default_config()
    pricing = default_pricing()
    _apply_search_overrides(config, pricing, args)
    runtime = _resolve_runtime(args.mode, getattr(args, "run_id", None))
    return config, pricing, runtime


def _resolve_runtime(mode: str, run_id: Optional[str]) -> RuntimeState:
    env = dict(os.environ)
    exa_api_key = (env.get("EXA_API_KEY") or "").strip()
    resolved_mode = mode
    if resolved_mode == "auto":
        resolved_mode = "live" if exa_api_key else "smoke"

    env["EXA_SMOKE_NO_NETWORK"] = "1" if resolved_mode == "smoke" else "0"
    if run_id:
        env["EXA_RUN_ID"] = run_id
    return load_runtime_state(env=env)


def _runtime_metadata(runtime: RuntimeState) -> Dict[str, Any]:
    execution_mode = "smoke" if runtime.smoke_no_network else "live"
    return {
        "execution_mode": execution_mode,
        "smoke_no_network": bool(runtime.smoke_no_network),
        "network_access": not bool(runtime.smoke_no_network),
        "api_key_configured": bool(runtime.exa_api_key),
    }

