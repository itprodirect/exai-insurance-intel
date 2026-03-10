from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import pandas as pd

from .cost_model import enforce_budget, summarize_ledger_rows


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def request_hash_for_payload(payload: Dict[str, Any]) -> str:
    return sha256_hex(canonical_json(payload))


def parse_actual_cost(response_json: Dict[str, Any]) -> Optional[float]:
    if isinstance(response_json, dict):
        cost = response_json.get("costDollars")
        if isinstance(cost, dict) and isinstance(cost.get("total"), (int, float)):
            return float(cost["total"])
    return None


class SqliteCacheStore:
    def __init__(self, sqlite_path: str | Path, cache_ttl_hours: float) -> None:
        self.sqlite_path = Path(sqlite_path)
        self.cache_ttl_hours = float(cache_ttl_hours)

    def _db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exa_cache (
                request_hash TEXT PRIMARY KEY,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                estimated_cost_usd REAL NOT NULL,
                actual_cost_usd REAL,
                created_at_utc TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exa_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                request_hash TEXT NOT NULL,
                query TEXT NOT NULL,
                cache_hit INTEGER NOT NULL,
                estimated_cost_usd REAL NOT NULL,
                actual_cost_usd REAL,
                created_at_utc TEXT NOT NULL
            )
            """
        )

        cols = [row[1] for row in conn.execute("PRAGMA table_info(exa_ledger)").fetchall()]
        if "run_id" not in cols:
            conn.execute("ALTER TABLE exa_ledger ADD COLUMN run_id TEXT")

        conn.commit()
        return conn

    def lookup(self, request_hash: str) -> Optional[Dict[str, Any]]:
        conn = self._db()
        try:
            row = conn.execute(
                "SELECT response_json, created_at_utc FROM exa_cache WHERE request_hash = ?",
                (request_hash,),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            return None

        response_json, created_at_utc = row
        try:
            created = datetime.fromisoformat(str(created_at_utc).replace("Z", "+00:00"))
        except ValueError:
            return None

        age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
        if age_hours > self.cache_ttl_hours:
            return None

        return json.loads(response_json)

    def store(
        self,
        request_hash: str,
        request_payload: Dict[str, Any],
        response_json: Dict[str, Any],
        estimated_cost: float,
    ) -> None:
        conn = self._db()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO exa_cache (request_hash, request_json, response_json, estimated_cost_usd, actual_cost_usd, created_at_utc) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    request_hash,
                    canonical_json(request_payload),
                    canonical_json(response_json),
                    float(estimated_cost),
                    parse_actual_cost(response_json),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def ledger_add(
        self,
        request_hash: str,
        query: str,
        cache_hit: bool,
        estimated_cost: float,
        actual_cost: Optional[float],
        *,
        run_id: str,
    ) -> None:
        conn = self._db()
        try:
            conn.execute(
                "INSERT INTO exa_ledger (run_id, request_hash, query, cache_hit, estimated_cost_usd, actual_cost_usd, created_at_utc) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    request_hash,
                    query,
                    1 if cache_hit else 0,
                    float(estimated_cost),
                    None if actual_cost is None else float(actual_cost),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def ledger_summary(self, run_id: Optional[str] = None) -> pd.DataFrame:
        conn = self._db()
        try:
            if run_id:
                df = pd.read_sql_query(
                    "SELECT * FROM exa_ledger WHERE run_id = ? ORDER BY id ASC",
                    conn,
                    params=[run_id],
                )
            else:
                df = pd.read_sql_query("SELECT * FROM exa_ledger ORDER BY id ASC", conn)
        finally:
            conn.close()

        expected_cols = [
            "id",
            "run_id",
            "request_hash",
            "query",
            "cache_hit",
            "estimated_cost_usd",
            "actual_cost_usd",
            "created_at_utc",
        ]
        if df.empty:
            return pd.DataFrame(columns=expected_cols)
        return df

    def spend_so_far(self, run_id: Optional[str] = None) -> Dict[str, float]:
        df = self.ledger_summary(run_id=run_id)
        if df.empty:
            return {
                "request_count": 0,
                "cache_hits": 0,
                "uncached_calls": 0,
                "spent_usd": 0.0,
                "avg_cost_per_uncached_query": 0.0,
            }
        return summarize_ledger_rows(df.to_dict(orient="records"))

    def get_or_set(
        self,
        payload: Dict[str, Any],
        estimated_cost: float,
        *,
        run_id: str,
        budget_cap_usd: float,
        fetcher: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], bool]:
        request_hash = request_hash_for_payload(payload)
        cached = self.lookup(request_hash)

        if cached is not None:
            self.ledger_add(
                request_hash=request_hash,
                query=str(payload.get("query") or ""),
                cache_hit=True,
                estimated_cost=estimated_cost,
                actual_cost=parse_actual_cost(cached),
                run_id=run_id,
            )
            return cached, True

        metrics = self.spend_so_far(run_id=run_id)
        enforce_budget(
            estimated_cost,
            spent_usd=float(metrics["spent_usd"]),
            budget_cap_usd=float(budget_cap_usd),
            run_id=run_id,
        )

        response_json = fetcher(payload)
        self.store(request_hash, payload, response_json, estimated_cost)
        self.ledger_add(
            request_hash=request_hash,
            query=str(payload.get("query") or ""),
            cache_hit=False,
            estimated_cost=estimated_cost,
            actual_cost=parse_actual_cost(response_json),
            run_id=run_id,
        )
        return response_json, False