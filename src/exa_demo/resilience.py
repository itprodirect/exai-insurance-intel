"""Circuit breaker and retry logic for external API calls."""

from __future__ import annotations

import logging
import random
import threading
import time
from typing import TypeVar

import requests

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Exceptions considered transient and eligible for retry / circuit-breaker tracking.
_TRANSIENT_HTTP_CODES = frozenset({429, 500, 502, 503, 504})


def is_transient(exc: BaseException) -> bool:
    """Return True if *exc* looks like a transient network/server error."""
    if isinstance(exc, requests.exceptions.ConnectionError):
        return True
    if isinstance(exc, requests.exceptions.Timeout):
        return True
    if isinstance(exc, requests.exceptions.HTTPError):
        resp = exc.response
        if resp is not None and resp.status_code in _TRANSIENT_HTTP_CODES:
            return True
    return False


class CircuitOpenError(RuntimeError):
    """Raised when a call is rejected because the circuit breaker is open."""

    def __init__(self, reset_at: float) -> None:
        remaining = max(0.0, reset_at - time.monotonic())
        super().__init__(
            f"Circuit breaker is open. Retry after {remaining:.1f}s."
        )
        self.reset_at = reset_at


class CircuitBreaker:
    """Lightweight circuit breaker with exponential-backoff retry.

    States
    ------
    CLOSED   – requests flow normally; consecutive failures are counted.
    OPEN     – requests are rejected immediately (raises ``CircuitOpenError``).
    HALF-OPEN – one probe request is allowed through to test recovery.

    Parameters
    ----------
    failure_threshold : int
        Consecutive transient failures before the breaker trips open.
    recovery_timeout : float
        Seconds to wait in OPEN state before allowing a probe (half-open).
    max_retries : int
        How many times to retry a transient failure *before* counting it as
        a circuit-breaker failure.  Set to 0 to disable retry.
    backoff_base : float
        Base delay (seconds) for exponential backoff between retries.
    backoff_max : float
        Maximum delay (seconds) between retries.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        max_retries: int = 2,
        backoff_base: float = 0.5,
        backoff_max: float = 10.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max

        self._lock = threading.Lock()
        self._state = self.CLOSED
        self._consecutive_failures = 0
        self._opened_at: float = 0.0

    # -- public API ----------------------------------------------------------

    @property
    def state(self) -> str:
        with self._lock:
            return self._current_state()

    def call(self, fn, *args, **kwargs):
        """Invoke *fn* with circuit-breaker protection and retry.

        Returns the result of *fn(*args, **kwargs)* on success.
        Raises ``CircuitOpenError`` if the breaker is open.
        Re-raises the original exception if all retries are exhausted.
        """
        self._check_state()

        last_exc: BaseException | None = None
        attempts = 1 + self.max_retries  # first try + retries

        for attempt in range(attempts):
            try:
                result = fn(*args, **kwargs)
                self._record_success()
                return result
            except Exception as exc:
                last_exc = exc
                if not is_transient(exc):
                    # Non-transient errors (4xx, auth, etc.) skip retry.
                    self._record_failure()
                    raise

                if attempt < attempts - 1:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        "Transient error (attempt %d/%d), retrying in %.2fs: %s",
                        attempt + 1,
                        attempts,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "All %d attempts exhausted: %s", attempts, exc
                    )
                    self._record_failure()
                    raise

        # Should not reach here, but satisfy type checker.
        raise last_exc  # type: ignore[misc]

    def reset(self) -> None:
        """Manually reset the breaker to closed state."""
        with self._lock:
            self._state = self.CLOSED
            self._consecutive_failures = 0
            self._opened_at = 0.0

    # -- internals -----------------------------------------------------------

    def _current_state(self) -> str:
        """Return effective state, promoting OPEN → HALF_OPEN when timeout expires."""
        if self._state == self.OPEN:
            if time.monotonic() >= self._opened_at + self.recovery_timeout:
                self._state = self.HALF_OPEN
        return self._state

    def _check_state(self) -> None:
        with self._lock:
            state = self._current_state()
            if state == self.OPEN:
                raise CircuitOpenError(
                    self._opened_at + self.recovery_timeout
                )
            # CLOSED and HALF_OPEN both allow the call through.

    def _record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            if self._state == self.HALF_OPEN:
                logger.info("Circuit breaker closing after successful probe.")
                self._state = self.CLOSED

    def _record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            if self._state == self.HALF_OPEN:
                # Probe failed → reopen immediately.
                logger.warning("Half-open probe failed, re-opening circuit.")
                self._state = self.OPEN
                self._opened_at = time.monotonic()
            elif self._consecutive_failures >= self.failure_threshold:
                logger.warning(
                    "Circuit breaker tripping open after %d consecutive failures.",
                    self._consecutive_failures,
                )
                self._state = self.OPEN
                self._opened_at = time.monotonic()

    def _backoff_delay(self, attempt: int) -> float:
        """Exponential backoff with full jitter."""
        delay = min(self.backoff_base * (2 ** attempt), self.backoff_max)
        return random.uniform(0, delay)
