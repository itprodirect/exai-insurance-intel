"""Tests for circuit breaker and retry logic."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import requests

from exa_demo.resilience import CircuitBreaker, CircuitOpenError, is_transient


# ---------------------------------------------------------------------------
# is_transient
# ---------------------------------------------------------------------------


def test_is_transient_connection_error() -> None:
    assert is_transient(requests.exceptions.ConnectionError()) is True


def test_is_transient_timeout() -> None:
    assert is_transient(requests.exceptions.Timeout()) is True


def test_is_transient_500() -> None:
    resp = MagicMock()
    resp.status_code = 502
    exc = requests.exceptions.HTTPError(response=resp)
    assert is_transient(exc) is True


def test_is_transient_400_not_transient() -> None:
    resp = MagicMock()
    resp.status_code = 400
    exc = requests.exceptions.HTTPError(response=resp)
    assert is_transient(exc) is False


def test_is_transient_runtime_error_not_transient() -> None:
    assert is_transient(RuntimeError("bad")) is False


# ---------------------------------------------------------------------------
# CircuitBreaker: basic success
# ---------------------------------------------------------------------------


def test_call_success_returns_result() -> None:
    cb = CircuitBreaker(failure_threshold=3, max_retries=0)
    result = cb.call(lambda: 42)
    assert result == 42
    assert cb.state == CircuitBreaker.CLOSED


def test_call_passes_args_and_kwargs() -> None:
    cb = CircuitBreaker(max_retries=0)
    result = cb.call(lambda a, b=0: a + b, 10, b=5)
    assert result == 15


# ---------------------------------------------------------------------------
# CircuitBreaker: retry on transient errors
# ---------------------------------------------------------------------------


def test_retry_on_transient_then_succeed() -> None:
    call_count = 0

    def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise requests.exceptions.ConnectionError("conn refused")
        return "ok"

    cb = CircuitBreaker(
        failure_threshold=5,
        max_retries=2,
        backoff_base=0.01,  # fast for tests
        backoff_max=0.02,
    )
    result = cb.call(flaky)
    assert result == "ok"
    assert call_count == 3
    assert cb.state == CircuitBreaker.CLOSED


def test_retry_exhausted_raises_and_counts_failure() -> None:
    cb = CircuitBreaker(
        failure_threshold=5,
        max_retries=1,
        backoff_base=0.01,
    )
    try:
        cb.call(_raise_connection_error)
        assert False, "Should have raised"
    except requests.exceptions.ConnectionError:
        pass
    # Should have counted one failure toward the breaker.
    assert cb._consecutive_failures == 1
    assert cb.state == CircuitBreaker.CLOSED


# ---------------------------------------------------------------------------
# CircuitBreaker: non-transient errors skip retry
# ---------------------------------------------------------------------------


def test_non_transient_error_not_retried() -> None:
    call_count = 0

    def bad_request():
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.status_code = 400
        raise requests.exceptions.HTTPError(response=resp)

    cb = CircuitBreaker(failure_threshold=5, max_retries=3, backoff_base=0.01)
    try:
        cb.call(bad_request)
        assert False, "Should have raised"
    except requests.exceptions.HTTPError:
        pass
    assert call_count == 1  # no retry


# ---------------------------------------------------------------------------
# CircuitBreaker: trip open
# ---------------------------------------------------------------------------


def test_trips_open_after_threshold() -> None:
    cb = CircuitBreaker(failure_threshold=3, max_retries=0, recovery_timeout=60.0)

    for _ in range(3):
        try:
            cb.call(_raise_connection_error)
        except requests.exceptions.ConnectionError:
            pass

    assert cb.state == CircuitBreaker.OPEN

    try:
        cb.call(lambda: "should not run")
        assert False, "Should have raised CircuitOpenError"
    except CircuitOpenError:
        pass


def test_success_resets_failure_count() -> None:
    cb = CircuitBreaker(failure_threshold=3, max_retries=0)

    # Two failures
    for _ in range(2):
        try:
            cb.call(_raise_connection_error)
        except requests.exceptions.ConnectionError:
            pass

    # A success should reset the counter
    cb.call(lambda: "ok")
    assert cb._consecutive_failures == 0

    # Two more failures should NOT trip the breaker (counter was reset)
    for _ in range(2):
        try:
            cb.call(_raise_connection_error)
        except requests.exceptions.ConnectionError:
            pass
    assert cb.state == CircuitBreaker.CLOSED


# ---------------------------------------------------------------------------
# CircuitBreaker: half-open → recovery
# ---------------------------------------------------------------------------


def test_half_open_probe_success_closes_circuit() -> None:
    cb = CircuitBreaker(failure_threshold=2, max_retries=0, recovery_timeout=0.05)

    # Trip the breaker
    for _ in range(2):
        try:
            cb.call(_raise_connection_error)
        except requests.exceptions.ConnectionError:
            pass
    assert cb.state == CircuitBreaker.OPEN

    # Wait for recovery timeout (generous margin for CI / Windows timer resolution)
    time.sleep(0.15)
    assert cb.state == CircuitBreaker.HALF_OPEN

    # Successful probe should close
    result = cb.call(lambda: "recovered")
    assert result == "recovered"
    assert cb.state == CircuitBreaker.CLOSED


def test_half_open_probe_failure_reopens() -> None:
    cb = CircuitBreaker(failure_threshold=2, max_retries=0, recovery_timeout=0.05)

    # Trip the breaker
    for _ in range(2):
        try:
            cb.call(_raise_connection_error)
        except requests.exceptions.ConnectionError:
            pass
    assert cb.state == CircuitBreaker.OPEN

    # Wait for recovery timeout (generous margin for CI / Windows timer resolution)
    time.sleep(0.15)
    assert cb.state == CircuitBreaker.HALF_OPEN

    # Failed probe should reopen
    try:
        cb.call(_raise_connection_error)
    except requests.exceptions.ConnectionError:
        pass
    assert cb.state == CircuitBreaker.OPEN


# ---------------------------------------------------------------------------
# CircuitBreaker: manual reset
# ---------------------------------------------------------------------------


def test_manual_reset() -> None:
    cb = CircuitBreaker(failure_threshold=2, max_retries=0, recovery_timeout=999)

    for _ in range(2):
        try:
            cb.call(_raise_connection_error)
        except requests.exceptions.ConnectionError:
            pass
    assert cb.state == CircuitBreaker.OPEN

    cb.reset()
    assert cb.state == CircuitBreaker.CLOSED
    result = cb.call(lambda: "after reset")
    assert result == "after reset"


# ---------------------------------------------------------------------------
# Integration: exa_http_call uses circuit breaker
# ---------------------------------------------------------------------------


def test_exa_http_call_smoke_bypasses_circuit_breaker() -> None:
    """Smoke mode should not touch the circuit breaker at all."""
    from exa_demo.client import exa_circuit_breaker, exa_http_call
    from exa_demo.config import default_config

    # Even if the breaker is open, smoke should work.
    exa_circuit_breaker.reset()
    exa_circuit_breaker._state = CircuitBreaker.OPEN
    exa_circuit_breaker._opened_at = time.monotonic()

    config = default_config()
    result = exa_http_call(
        {"query": "test", "numResults": 1},
        config=config,
        exa_api_key="",
        smoke_no_network=True,
    )
    assert "results" in result

    # Clean up
    exa_circuit_breaker.reset()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_connection_error():
    raise requests.exceptions.ConnectionError("connection refused")
