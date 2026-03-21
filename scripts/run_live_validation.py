from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping

WORKFLOW_REQUIRED_PAYLOAD_KEYS: Dict[str, tuple[str, ...]] = {
    "search": ("run_id", "artifact_dir", "record", "summary"),
    "answer": ("workflow", "run_id", "artifact_dir", "answer", "citation_count", "summary"),
    "research": ("workflow", "run_id", "artifact_dir", "report", "citation_count", "summary"),
    "structured-search": ("workflow", "run_id", "artifact_dir", "structured_output", "summary"),
    "find-similar": ("workflow", "run_id", "artifact_dir", "result_count", "summary"),
}

WORKFLOW_REQUIRED_ARTIFACTS: Dict[str, tuple[str, ...]] = {
    "search": ("summary.json", "results.jsonl"),
    "answer": ("summary.json", "answer.json"),
    "research": ("summary.json", "research.json", "research.md"),
    "structured-search": ("summary.json", "structured_output.json"),
    "find-similar": ("summary.json", "find_similar.json"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a bounded set of Exa workflow validations through the CLI."
    )
    parser.add_argument(
        "--mode",
        choices=["smoke", "live", "auto"],
        default="auto",
        help="Execution mode: smoke=no network/billing, live=real API calls, auto=live if EXA_API_KEY is present else smoke.",
    )
    parser.add_argument(
        "--artifact-dir",
        default="live-validation-artifacts",
        help="Base directory for validation artifacts.",
    )
    parser.add_argument(
        "--run-id-prefix",
        help="Optional prefix for generated run ids. Defaults to a UTC timestamped live-validation label.",
    )
    parser.add_argument(
        "--include-comparison",
        action="store_true",
        help="Also run the compare-search-types workflow. This is more expensive than the default validation set.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    artifact_dir = repo_root / args.artifact_dir
    artifact_dir.mkdir(parents=True, exist_ok=True)

    mode = _resolve_mode(args.mode)
    if mode == "live" and not (os.getenv("EXA_API_KEY") or "").strip():
        print("Mode=live requested but EXA_API_KEY is missing.", file=sys.stderr)
        return 1

    os.environ["EXA_SMOKE_NO_NETWORK"] = "1" if mode == "smoke" else "0"
    print(
        "Mode=smoke: EXA_SMOKE_NO_NETWORK=1 (no network/API billing)."
        if mode == "smoke"
        else "Mode=live: using Exa API for bounded manual validation."
    )

    run_id_prefix = args.run_id_prefix or _default_run_id_prefix()
    commands = build_validation_commands(
        repo_root=repo_root,
        artifact_dir=artifact_dir,
        run_id_prefix=run_id_prefix,
        mode=mode,
        include_comparison=bool(args.include_comparison),
    )

    summary_rows: List[Dict[str, Any]] = []
    for command in commands:
        summary_rows.append(
            _run_validation_command(
                command,
                artifact_dir=artifact_dir,
                mode=mode,
            )
        )

    summary_path = artifact_dir / "validation_summary.json"
    summary_payload = {
        "mode": mode,
        "run_id_prefix": run_id_prefix,
        "artifact_dir": str(artifact_dir),
        "commands": summary_rows,
    }
    summary_path.write_text(json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Validation summary written to: {summary_path}")
    return 0


def build_validation_commands(
    *,
    repo_root: Path,
    artifact_dir: Path,
    run_id_prefix: str,
    mode: str,
    include_comparison: bool,
) -> List[Dict[str, Any]]:
    schema_path = repo_root / "assets" / "live_validation_schema.json"
    base_command = [sys.executable, "-m", "exa_demo"]

    commands: List[Dict[str, Any]] = [
        {
            "name": "search",
            "run_id": f"{run_id_prefix}-search",
            "argv": base_command
            + [
                "search",
                "forensic engineer insurance expert witness",
                "--mode",
                mode,
                "--run-id",
                f"{run_id_prefix}-search",
                "--artifact-dir",
                str(artifact_dir),
                "--json",
            ],
        },
        {
            "name": "answer",
            "run_id": f"{run_id_prefix}-answer",
            "argv": base_command
            + [
                "answer",
                "What is the Florida appraisal clause dispute process?",
                "--mode",
                mode,
                "--run-id",
                f"{run_id_prefix}-answer",
                "--artifact-dir",
                str(artifact_dir),
                "--json",
            ],
        },
        {
            "name": "research",
            "run_id": f"{run_id_prefix}-research",
            "argv": base_command
            + [
                "research",
                "Summarize the Florida CAT market outlook.",
                "--mode",
                mode,
                "--run-id",
                f"{run_id_prefix}-research",
                "--artifact-dir",
                str(artifact_dir),
                "--json",
            ],
        },
        {
            "name": "structured-search",
            "run_id": f"{run_id_prefix}-structured",
            "argv": base_command
            + [
                "structured-search",
                "independent adjuster florida catastrophe claims",
                "--schema-file",
                str(schema_path),
                "--mode",
                mode,
                "--run-id",
                f"{run_id_prefix}-structured",
                "--artifact-dir",
                str(artifact_dir),
                "--json",
            ],
        },
        {
            "name": "find-similar",
            "run_id": f"{run_id_prefix}-find-similar",
            "argv": base_command
            + [
                "find-similar",
                "https://www.merlinlawgroup.com/",
                "--mode",
                mode,
                "--run-id",
                f"{run_id_prefix}-find-similar",
                "--artifact-dir",
                str(artifact_dir),
                "--json",
            ],
        },
    ]

    if include_comparison:
        commands.append(
            {
                "name": "compare-search-types",
                "run_id": f"{run_id_prefix}-compare",
                "argv": base_command
                + [
                    "compare-search-types",
                    "--mode",
                    mode,
                    "--run-id",
                    f"{run_id_prefix}-compare",
                    "--artifact-dir",
                    str(artifact_dir),
                    "--suite",
                    "forensic_and_damage_engineering",
                    "--limit",
                    "2",
                    "--baseline-type",
                    "deep",
                    "--candidate-type",
                    "deep-reasoning",
                    "--json",
                ],
            }
        )

    return commands


def _run_validation_command(
    command: Dict[str, Any],
    *,
    artifact_dir: Path,
    mode: str,
) -> Dict[str, Any]:
    argv = [str(part) for part in command["argv"]]
    print(f"Running validation command: {command['name']}")
    completed = subprocess.run(
        argv,
        cwd=artifact_dir.parents[0],
        capture_output=True,
        text=True,
        check=False,
        env=dict(os.environ),
    )
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"Validation command failed: {command['name']}")

    stdout_payload = _parse_json_output(completed.stdout, command["name"])
    validation = _validate_command_output(
        command_name=command["name"],
        expected_run_id=command["run_id"],
        payload=stdout_payload,
        artifact_dir=artifact_dir,
        mode=mode,
    )
    return {
        "name": command["name"],
        "mode": mode,
        "run_id": command["run_id"],
        "artifact_dir": validation["artifact_dir"],
        "request_id": validation["request_id"],
        "request_id_present": bool(validation["request_id"]),
        "validated_artifacts": validation["validated_artifacts"],
    }


def _parse_json_output(raw_output: str, command_name: str) -> Dict[str, Any]:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Validation command did not emit JSON: {command_name}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Validation command emitted unexpected payload type: {command_name}")
    return payload


def _validate_command_output(
    *,
    command_name: str,
    expected_run_id: str,
    payload: Mapping[str, Any],
    artifact_dir: Path,
    mode: str,
) -> Dict[str, Any]:
    if command_name == "compare-search-types":
        return _validate_compare_search_types_output(
            payload=payload,
            expected_run_id=expected_run_id,
            artifact_dir=artifact_dir,
        )
    return _validate_single_workflow_output(
        command_name=command_name,
        expected_run_id=expected_run_id,
        payload=payload,
        artifact_dir=artifact_dir,
        mode=mode,
    )


def _validate_single_workflow_output(
    *,
    command_name: str,
    expected_run_id: str,
    payload: Mapping[str, Any],
    artifact_dir: Path,
    mode: str,
) -> Dict[str, Any]:
    required_keys = WORKFLOW_REQUIRED_PAYLOAD_KEYS[command_name]
    missing_keys = [key for key in required_keys if key not in payload]
    if missing_keys:
        joined = ", ".join(missing_keys)
        raise RuntimeError(f"Validation payload missing keys for {command_name}: {joined}")

    run_id = str(payload.get("run_id") or "").strip()
    if run_id != expected_run_id:
        raise RuntimeError(
            f"Validation payload emitted unexpected run_id for {command_name}: {run_id!r}"
        )

    expected_workflow = None if command_name == "search" else command_name
    if expected_workflow and str(payload.get("workflow") or "").strip() != expected_workflow:
        raise RuntimeError(
            f"Validation payload emitted unexpected workflow for {command_name}: "
            f"{payload.get('workflow')!r}"
        )

    request_id = _extract_request_id(payload)
    if mode == "live" and not request_id:
        raise RuntimeError(f"Validation payload missing request_id for live command: {command_name}")

    resolved_artifact_dir = _resolve_artifact_dir(
        artifact_dir=artifact_dir,
        artifact_path_value=payload.get("artifact_dir"),
        command_name=command_name,
    )
    validated_artifacts = _require_artifacts(
        resolved_artifact_dir,
        required_filenames=WORKFLOW_REQUIRED_ARTIFACTS[command_name],
        command_name=command_name,
    )
    return {
        "artifact_dir": str(resolved_artifact_dir),
        "request_id": request_id,
        "validated_artifacts": validated_artifacts,
    }


def _validate_compare_search_types_output(
    *,
    payload: Mapping[str, Any],
    expected_run_id: str,
    artifact_dir: Path,
) -> Dict[str, Any]:
    required_keys = (
        "workflow",
        "base_run_id",
        "baseline_run",
        "candidate_run",
        "comparison",
        "comparison_markdown_path",
    )
    missing_keys = [key for key in required_keys if key not in payload]
    if missing_keys:
        joined = ", ".join(missing_keys)
        raise RuntimeError(
            f"Validation payload missing keys for compare-search-types: {joined}"
        )

    if str(payload.get("workflow") or "").strip() != "compare-search-types":
        raise RuntimeError("Validation payload emitted unexpected workflow for compare-search-types.")
    if str(payload.get("base_run_id") or "").strip() != expected_run_id:
        raise RuntimeError("Validation payload emitted unexpected base_run_id for compare-search-types.")

    baseline_run = payload.get("baseline_run")
    candidate_run = payload.get("candidate_run")
    if not isinstance(baseline_run, dict) or not isinstance(candidate_run, dict):
        raise RuntimeError("compare-search-types payload must include baseline_run and candidate_run objects.")

    baseline_dir = _resolve_artifact_dir(
        artifact_dir=artifact_dir,
        artifact_path_value=baseline_run.get("artifact_dir"),
        command_name="compare-search-types baseline",
    )
    candidate_dir = _resolve_artifact_dir(
        artifact_dir=artifact_dir,
        artifact_path_value=candidate_run.get("artifact_dir"),
        command_name="compare-search-types candidate",
    )
    validated_artifacts = _require_artifacts(
        baseline_dir,
        required_filenames=("summary.json", "results.jsonl"),
        command_name="compare-search-types baseline",
    )
    validated_artifacts.extend(
        _require_artifacts(
            candidate_dir,
            required_filenames=("summary.json", "comparison.json"),
            command_name="compare-search-types candidate",
        )
    )

    markdown_path = Path(str(payload.get("comparison_markdown_path") or ""))
    if not markdown_path.is_absolute():
        markdown_path = (candidate_dir / markdown_path).resolve()
    else:
        markdown_path = markdown_path.resolve()
    if not markdown_path.is_relative_to(candidate_dir):
        raise RuntimeError("compare-search-types comparison markdown escaped the candidate artifact directory.")
    if not markdown_path.exists():
        raise RuntimeError("compare-search-types did not emit comparison markdown.")
    validated_artifacts.append(str(markdown_path))

    return {
        "artifact_dir": str(candidate_dir),
        "request_id": None,
        "validated_artifacts": validated_artifacts,
    }


def _extract_request_id(payload: Mapping[str, Any]) -> str | None:
    top_level = str(payload.get("request_id") or "").strip()
    if top_level:
        return top_level

    record = payload.get("record")
    if isinstance(record, Mapping):
        nested = str(record.get("request_id") or "").strip()
        if nested:
            return nested
    return None


def _resolve_artifact_dir(
    *,
    artifact_dir: Path,
    artifact_path_value: Any,
    command_name: str,
) -> Path:
    text = str(artifact_path_value or "").strip()
    if not text:
        raise RuntimeError(f"Validation payload missing artifact_dir for {command_name}.")
    resolved_path = Path(text)
    if not resolved_path.is_absolute():
        resolved_path = (artifact_dir.parent / resolved_path).resolve()
    else:
        resolved_path = resolved_path.resolve()
    artifact_root = artifact_dir.resolve()
    if not resolved_path.is_relative_to(artifact_root):
        raise RuntimeError(f"Validation artifact_dir escaped the expected artifact root for {command_name}.")
    if not resolved_path.exists():
        raise RuntimeError(f"Validation artifact_dir does not exist for {command_name}: {resolved_path}")
    return resolved_path


def _require_artifacts(
    run_dir: Path,
    *,
    required_filenames: tuple[str, ...],
    command_name: str,
) -> List[str]:
    validated: List[str] = []
    for filename in required_filenames:
        path = run_dir / filename
        if not path.exists():
            raise RuntimeError(f"Validation artifact missing for {command_name}: {path}")
        validated.append(str(path))
    return validated


def _default_run_id_prefix() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"live-validation-{timestamp}"


def _resolve_mode(mode: str) -> str:
    if mode != "auto":
        return mode
    return "live" if (os.getenv("EXA_API_KEY") or "").strip() else "smoke"


if __name__ == "__main__":
    raise SystemExit(main())
