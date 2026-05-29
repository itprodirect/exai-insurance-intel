"""Bounded real S3/Postgres persistence validation for the pilot API."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlencode, urlparse


REQUIRED_RUN_STORE = "postgres"
REQUIRED_ARTIFACT_STORE = "s3"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_RESULT_LIMIT = 25
DEFAULT_VALIDATION_PREFIX = "validation/pilot-persistence/"

SECRET_ENV_NAMES = (
    "PILOT_POSTGRES_URL",
    "PILOT_API_KEY",
    "PILOT_VALIDATION_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "EXA_API_KEY",
)


class PersistenceValidationError(RuntimeError):
    """Raised when real persistence validation cannot pass."""


class PersistenceValidationConfigError(PersistenceValidationError):
    """Raised when required external validation configuration is absent."""


@dataclass(frozen=True)
class ValidationConfig:
    """Runtime options for the bounded API validation."""

    repo_root: Path
    base_url: str | None
    host: str
    port: int | None
    timeout_seconds: float
    query: str
    run_id: str
    api_key: str | None
    output_path: Path | None
    result_limit: int = DEFAULT_RESULT_LIMIT


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one smoke API workflow with PILOT_RUN_STORE=postgres and "
            "PILOT_ARTIFACT_STORE=s3 selected, then verify persisted run "
            "metadata and S3 artifact evidence."
        )
    )
    parser.add_argument(
        "--base-url",
        help=(
            "Use an already-running API instead of starting uvicorn. "
            "The API must already be configured for postgres/s3."
        ),
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument(
        "--port",
        type=int,
        help="Port for the temporary uvicorn process. Defaults to a free port.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Seconds to wait for API startup and persisted run visibility.",
    )
    parser.add_argument(
        "--query",
        help="Optional validation query marker. Defaults to a UTC timestamp.",
    )
    parser.add_argument(
        "--run-id",
        help=(
            "Run id to inject into the temporary API process. Ignored when "
            "--base-url is used with an already-running API."
        ),
    )
    parser.add_argument(
        "--api-key-env",
        default="PILOT_VALIDATION_API_KEY",
        help=(
            "Environment variable containing the bearer token to send. "
            "Falls back to PILOT_API_KEY when this variable is unset."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the JSON evidence summary.",
    )
    parser.add_argument(
        "--result-limit",
        type=int,
        default=DEFAULT_RESULT_LIMIT,
        help="Number of recent /api/me/runs records to inspect.",
    )
    return parser.parse_args(argv)


def config_from_args(
    args: argparse.Namespace,
    *,
    repo_root: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> ValidationConfig:
    env = env or os.environ
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"pilot-persistence-{timestamp}"
    query = args.query or f"Pilot S3/Postgres validation {run_id}"
    api_key = (
        env.get(args.api_key_env, "").strip()
        or env.get("PILOT_API_KEY", "").strip()
        or None
    )
    return ValidationConfig(
        repo_root=(repo_root or Path.cwd()).resolve(),
        base_url=_normalize_base_url(args.base_url),
        host=args.host,
        port=args.port,
        timeout_seconds=args.timeout,
        query=query,
        run_id=run_id,
        api_key=api_key,
        output_path=args.output,
        result_limit=args.result_limit,
    )


def required_external_config_errors(env: Mapping[str, str]) -> list[str]:
    """Return missing/mismatched config that would make validation ambiguous."""

    errors: list[str] = []
    run_store = env.get("PILOT_RUN_STORE", "").strip().lower()
    if run_store != REQUIRED_RUN_STORE:
        errors.append("PILOT_RUN_STORE must be set to postgres.")

    artifact_store = env.get("PILOT_ARTIFACT_STORE", "").strip().lower()
    if artifact_store != REQUIRED_ARTIFACT_STORE:
        errors.append("PILOT_ARTIFACT_STORE must be set to s3.")

    if not env.get("PILOT_POSTGRES_URL", "").strip():
        errors.append("PILOT_POSTGRES_URL must point to a reachable Postgres DB.")

    if not env.get("PILOT_S3_BUCKET", "").strip():
        errors.append("PILOT_S3_BUCKET must name the validation S3 bucket.")

    if not env.get("PILOT_S3_PREFIX", "").strip():
        errors.append(
            "PILOT_S3_PREFIX must be set to a validation-scoped prefix, "
            f"for example {DEFAULT_VALIDATION_PREFIX}."
        )

    return errors


def run_validation(
    config: ValidationConfig,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    env = dict(env or os.environ)
    config_errors = required_external_config_errors(env)
    if config_errors:
        joined = "\n".join(f"- {error}" for error in config_errors)
        raise PersistenceValidationConfigError(
            "Real S3/Postgres validation was not run because required "
            f"configuration is missing or local-only:\n{joined}"
        )

    if config.base_url:
        return _run_against_api(config.base_url, config, env=env)

    port = config.port or _find_free_port(config.host)
    base_url = f"http://{config.host}:{port}"
    process = _start_api_process(config, port=port, env=env)
    try:
        _wait_for_health(
            base_url,
            timeout_seconds=config.timeout_seconds,
            process=process,
            env=env,
        )
        return _run_against_api(base_url, config, env=env)
    finally:
        _stop_process(process)


def _run_against_api(
    base_url: str,
    config: ValidationConfig,
    *,
    env: Mapping[str, str],
) -> dict[str, Any]:
    headers = _auth_headers(config.api_key)
    health = _request_json("GET", f"{base_url}/health", headers=headers)
    validate_external_health(health)

    search_payload = {
        "query": config.query,
        "mode": "smoke",
        "num_results": 1,
    }
    search_result = _request_json(
        "POST",
        f"{base_url}/api/search",
        payload=search_payload,
        headers=headers,
    )
    api_run_id = str(search_result.get("run_id") or "").strip()
    if not api_run_id:
        raise PersistenceValidationError("API search response did not include run_id.")

    record = _wait_for_matching_run(
        base_url,
        config=config,
        api_run_id=api_run_id,
        headers=headers,
    )
    artifact_location = validate_persisted_record(
        record,
        bucket=env["PILOT_S3_BUCKET"].strip(),
        prefix=env["PILOT_S3_PREFIX"].strip(),
        api_run_id=api_run_id,
        query=config.query,
    )
    s3_object_count = count_s3_objects(artifact_location)
    artifact_count = int(record.get("artifact_count") or 0)
    if s3_object_count < artifact_count:
        raise PersistenceValidationError(
            "S3 object count is lower than the persisted artifact_count "
            f"({s3_object_count} < {artifact_count})."
        )

    return {
        "validation": "pilot-s3-postgres-persistence",
        "status": "passed",
        "mode": "smoke",
        "health": health,
        "query_marker": config.query,
        "api_run_id": api_run_id,
        "run_record_id": record.get("id"),
        "run_record_user_id": record.get("user_id"),
        "artifact_location": artifact_location,
        "artifact_count": artifact_count,
        "s3_object_count": s3_object_count,
        "postgres_evidence": {
            "source": "/api/me/runs",
            "run_store": health.get("run_store"),
            "record_status": record.get("status"),
        },
        "s3_evidence": {
            "bucket": env["PILOT_S3_BUCKET"].strip(),
            "prefix": _s3_prefix_from_location(artifact_location),
            "artifact_store": health.get("artifact_store"),
        },
    }


def validate_external_health(health: Mapping[str, Any]) -> None:
    if health.get("status") != "ok":
        raise PersistenceValidationError(f"Unexpected health status: {health!r}")
    if health.get("run_store") != REQUIRED_RUN_STORE:
        raise PersistenceValidationError(
            "API health did not report run_store=postgres; "
            f"got {health.get('run_store')!r}."
        )
    if health.get("artifact_store") != REQUIRED_ARTIFACT_STORE:
        raise PersistenceValidationError(
            "API health did not report artifact_store=s3; "
            f"got {health.get('artifact_store')!r}."
        )


def find_matching_run(
    runs_payload: Mapping[str, Any],
    *,
    query: str,
    api_run_id: str,
) -> Mapping[str, Any] | None:
    runs = runs_payload.get("runs")
    if not isinstance(runs, list):
        raise PersistenceValidationError("/api/me/runs response did not include runs.")

    for item in runs:
        if not isinstance(item, Mapping):
            continue
        if item.get("run_id") == api_run_id and item.get("query_preview") == query:
            return item
    return None


def validate_persisted_record(
    record: Mapping[str, Any],
    *,
    bucket: str,
    prefix: str,
    api_run_id: str,
    query: str,
) -> str:
    if record.get("workflow") != "search":
        raise PersistenceValidationError("Persisted run workflow was not search.")
    if record.get("mode") != "smoke":
        raise PersistenceValidationError("Persisted run mode was not smoke.")
    if record.get("status") != "completed":
        raise PersistenceValidationError("Persisted run did not complete.")
    if record.get("query_preview") != query:
        raise PersistenceValidationError("Persisted run query marker did not match.")

    artifact_count = int(record.get("artifact_count") or 0)
    if artifact_count < 1:
        raise PersistenceValidationError(
            "Persisted run did not record uploaded artifacts."
        )

    artifact_location = str(record.get("artifact_location") or "").strip()
    expected = expected_s3_location(
        bucket=bucket,
        prefix=prefix,
        api_run_id=api_run_id,
    )
    if artifact_location != expected:
        raise PersistenceValidationError(
            "Persisted artifact_location did not match the selected S3 store "
            f"({artifact_location!r} != {expected!r})."
        )
    return artifact_location


def expected_s3_location(*, bucket: str, prefix: str, api_run_id: str) -> str:
    normalized_prefix = prefix.strip().rstrip("/") + "/"
    return f"s3://{bucket.strip()}/{normalized_prefix}{api_run_id}/"


def count_s3_objects(artifact_location: str) -> int:
    parsed = urlparse(artifact_location)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.strip("/"):
        raise PersistenceValidationError(
            f"Invalid S3 artifact location: {artifact_location!r}"
        )

    import boto3  # type: ignore[import-untyped]

    prefix = parsed.path.lstrip("/")
    response = boto3.client("s3").list_objects_v2(
        Bucket=parsed.netloc,
        Prefix=prefix,
    )
    return len(response.get("Contents", []))


def _wait_for_matching_run(
    base_url: str,
    *,
    config: ValidationConfig,
    api_run_id: str,
    headers: Mapping[str, str],
) -> Mapping[str, Any]:
    deadline = time.monotonic() + config.timeout_seconds
    params = urlencode(
        {
            "workflow": "search",
            "status": "completed",
            "limit": str(config.result_limit),
            "offset": "0",
        }
    )
    url = f"{base_url}/api/me/runs?{params}"
    last_payload: Mapping[str, Any] | None = None

    while time.monotonic() < deadline:
        payload = _request_json("GET", url, headers=headers)
        last_payload = payload
        record = find_matching_run(
            payload,
            query=config.query,
            api_run_id=api_run_id,
        )
        if record is not None:
            return record
        time.sleep(0.5)

    raise PersistenceValidationError(
        "Timed out waiting for the API to expose the persisted run through "
        f"/api/me/runs. Last response: {last_payload!r}"
    )


def _request_json(
    method: str,
    url: str,
    *,
    payload: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    body = None
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="replace")
        raise PersistenceValidationError(
            f"HTTP {exc.code} from {method} {url}: {raw_error}"
        ) from exc
    except urllib.error.URLError as exc:
        raise PersistenceValidationError(
            f"Could not reach API at {url}: {exc.reason}"
        ) from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PersistenceValidationError(
            f"API response was not JSON for {method} {url}: {raw!r}"
        ) from exc
    if not isinstance(parsed, dict):
        raise PersistenceValidationError(
            f"API response was not a JSON object for {method} {url}."
        )
    return parsed


def _wait_for_health(
    base_url: str,
    *,
    timeout_seconds: float,
    process: subprocess.Popen[str],
    env: Mapping[str, str],
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = _process_output(process, env)
            raise PersistenceValidationError(
                "API process exited before health check passed "
                f"(exit {process.returncode}). {output}"
            )
        try:
            _request_json("GET", f"{base_url}/health", timeout=2.0)
            return
        except PersistenceValidationError as exc:
            last_error = exc
            time.sleep(0.5)
    raise PersistenceValidationError(
        f"Timed out waiting for API health at {base_url}/health. "
        f"Last error: {last_error}"
    )


def _start_api_process(
    config: ValidationConfig,
    *,
    port: int,
    env: Mapping[str, str],
) -> subprocess.Popen[str]:
    process_env = dict(env)
    process_env["EXA_SMOKE_NO_NETWORK"] = "1"
    process_env["EXA_RUN_ID"] = config.run_id
    argv = [
        sys.executable,
        "-m",
        "uvicorn",
        "exa_demo.api:app",
        "--host",
        config.host,
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    return subprocess.Popen(
        argv,
        cwd=config.repo_root,
        env=process_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _process_output(
    process: subprocess.Popen[str],
    env: Mapping[str, str],
) -> str:
    stdout, stderr = process.communicate(timeout=2)
    pieces = []
    if stdout:
        pieces.append(f"stdout={_sanitize_output(stdout, env)}")
    if stderr:
        pieces.append(f"stderr={_sanitize_output(stderr, env)}")
    return " ".join(pieces)


def _sanitize_output(text: str, env: Mapping[str, str]) -> str:
    sanitized = text[-4000:]
    for name in SECRET_ENV_NAMES:
        value = env.get(name, "").strip()
        if len(value) >= 4:
            sanitized = sanitized.replace(value, f"<redacted:{name}>")
    return sanitized


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _find_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _auth_headers(api_key: str | None) -> dict[str, str]:
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}


def _normalize_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    return base_url.rstrip("/")


def _s3_prefix_from_location(artifact_location: str) -> str:
    parsed = urlparse(artifact_location)
    return parsed.path.lstrip("/")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = config_from_args(args)
    try:
        result = run_validation(config)
    except PersistenceValidationConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Pilot persistence validation failed: {exc}", file=sys.stderr)
        return 1

    output = json.dumps(result, indent=2, sort_keys=True)
    print(output)
    if config.output_path is not None:
        config.output_path.parent.mkdir(parents=True, exist_ok=True)
        config.output_path.write_text(output + "\n", encoding="utf-8")
    return 0
