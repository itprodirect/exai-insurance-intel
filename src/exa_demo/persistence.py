"""Pilot persistence layer for run metadata and artifact storage.

Provides two abstractions:

1. **ArtifactStore** — upload/list experiment artifacts (local filesystem or S3).
2. **RunRepository** — persist and query run metadata (local SQLite or Postgres).

Configuration via environment variables:

    PILOT_ARTIFACT_STORE       "local" (default) or "s3"
    PILOT_S3_BUCKET            S3 bucket name (required when store is "s3")
    PILOT_S3_PREFIX            Key prefix inside the bucket (default: "artifacts/")

    PILOT_RUN_STORE            "local" (default) or "postgres"
    PILOT_RUN_STORE_PATH       SQLite path for local store (default: "pilot_runs.sqlite")
    PILOT_POSTGRES_URL         Connection string (required when store is "postgres")
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger("exa_demo.persistence")


# ---------------------------------------------------------------------------
# Run record
# ---------------------------------------------------------------------------


@dataclass
class RunRecord:
    """Metadata for a single API-driven workflow run."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    request_id: Optional[str] = None
    run_id: Optional[str] = None
    workflow: str = ""
    mode: str = "smoke"
    status: str = "pending"  # pending | completed | failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    query_preview: Optional[str] = None
    cache_hit: Optional[bool] = None
    cost_summary: Optional[Dict[str, Any]] = None
    artifact_location: Optional[str] = None
    artifact_count: int = 0
    error_message: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # JSON-encode nested dicts for flat storage.
        for key in ("cost_summary", "extra"):
            if d[key] is not None:
                d[key] = json.dumps(d[key])
        return d

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> RunRecord:
        d = dict(row)
        for key in ("cost_summary", "extra"):
            if d.get(key) and isinstance(d[key], str):
                d[key] = json.loads(d[key])
        return cls(**d)


@dataclass
class SavedQuery:
    """A user-saved query for replay."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    user_id: str = ""
    workflow: str = ""
    query: str = ""
    label: Optional[str] = None
    created_at: Optional[str] = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _query_preview(text: Optional[str], max_len: int = 200) -> Optional[str]:
    """Truncate query/input to a safe preview length."""
    if not text:
        return None
    return text[:max_len] + ("..." if len(text) > max_len else "")


# ---------------------------------------------------------------------------
# Artifact store protocol + adapters
# ---------------------------------------------------------------------------


class ArtifactStore(Protocol):
    """Interface for storing and listing experiment artifacts."""

    def upload(self, run_id: str, filename: str, local_path: str | Path) -> str:
        """Upload a single file. Returns the remote/canonical location."""
        ...

    def upload_directory(self, run_id: str, local_dir: str | Path) -> List[str]:
        """Upload all files in a directory. Returns locations."""
        ...

    def list_artifacts(self, run_id: str) -> List[str]:
        """List stored artifact locations for a run."""
        ...


class LocalArtifactStore:
    """Artifact store backed by the local filesystem.

    For local dev, artifacts are already on disk in the experiment directory.
    This adapter records their canonical paths and supports an optional copy
    to a separate managed directory.
    """

    def __init__(self, base_dir: str | Path = "artifacts_store"):
        self.base_dir = Path(base_dir)

    def upload(self, run_id: str, filename: str, local_path: str | Path) -> str:
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Artifact not found: {local_path}")
        dest_dir = self.base_dir / run_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename
        if local_path.resolve() != dest.resolve():
            shutil.copy2(local_path, dest)
        return str(dest)

    def upload_directory(self, run_id: str, local_dir: str | Path) -> List[str]:
        local_dir = Path(local_dir)
        if not local_dir.is_dir():
            return []
        locations: List[str] = []
        for path in sorted(local_dir.iterdir()):
            if path.is_file():
                loc = self.upload(run_id, path.name, path)
                locations.append(loc)
        return locations

    def list_artifacts(self, run_id: str) -> List[str]:
        run_dir = self.base_dir / run_id
        if not run_dir.is_dir():
            return []
        return [str(p) for p in sorted(run_dir.iterdir()) if p.is_file()]


class S3ArtifactStore:
    """Artifact store backed by Amazon S3.

    Requires ``boto3`` (install via ``pip install boto3``).
    """

    def __init__(self, bucket: str, prefix: str = "artifacts/"):
        self.bucket = bucket
        self.prefix = prefix.rstrip("/") + "/"
        self._client = None

    @property
    def client(self):  # type: ignore[no-untyped-def]
        if self._client is None:
            import boto3  # type: ignore[import-untyped]

            self._client = boto3.client("s3")
        return self._client

    def _key(self, run_id: str, filename: str) -> str:
        return f"{self.prefix}{run_id}/{filename}"

    def upload(self, run_id: str, filename: str, local_path: str | Path) -> str:
        key = self._key(run_id, filename)
        self.client.upload_file(str(local_path), self.bucket, key)
        location = f"s3://{self.bucket}/{key}"
        logger.info("Uploaded %s -> %s", local_path, location)
        return location

    def upload_directory(self, run_id: str, local_dir: str | Path) -> List[str]:
        local_dir = Path(local_dir)
        if not local_dir.is_dir():
            return []
        locations: List[str] = []
        for path in sorted(local_dir.iterdir()):
            if path.is_file():
                loc = self.upload(run_id, path.name, path)
                locations.append(loc)
        return locations

    def list_artifacts(self, run_id: str) -> List[str]:
        prefix = f"{self.prefix}{run_id}/"
        resp = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return [
            f"s3://{self.bucket}/{obj['Key']}"
            for obj in resp.get("Contents", [])
        ]


# ---------------------------------------------------------------------------
# Run repository protocol + adapters
# ---------------------------------------------------------------------------


class RunRepository(Protocol):
    """Interface for persisting and querying run metadata."""

    def save(self, record: RunRecord) -> None:
        ...

    def get(self, record_id: str) -> Optional[RunRecord]:
        ...

    def list_runs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        workflow: Optional[str] = None,
        mode: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[RunRecord]:
        ...

    def summary(self) -> Dict[str, Any]:
        ...

    def user_summary(self, user_id: str) -> Dict[str, Any]:
        ...

    def save_query(self, sq: SavedQuery) -> None:
        ...

    def list_saved_queries(self, user_id: str) -> List[SavedQuery]:
        ...

    def delete_saved_query(self, query_id: str, user_id: str) -> bool:
        ...


_LOCAL_SCHEMA = """\
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    request_id TEXT,
    run_id TEXT,
    workflow TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'smoke',
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TEXT,
    completed_at TEXT,
    duration_ms REAL,
    query_preview TEXT,
    cache_hit INTEGER,
    cost_summary TEXT,
    artifact_location TEXT,
    artifact_count INTEGER DEFAULT 0,
    error_message TEXT,
    extra TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_run_id ON runs(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);
"""

_MIGRATION_ADD_DURATION = """\
ALTER TABLE runs ADD COLUMN duration_ms REAL;
"""

_MIGRATION_ADD_ERROR = """\
ALTER TABLE runs ADD COLUMN error_message TEXT;
"""

_MIGRATION_ADD_USER_ID = """\
ALTER TABLE runs ADD COLUMN user_id TEXT;
"""

_SAVED_QUERIES_SCHEMA = """\
CREATE TABLE IF NOT EXISTS saved_queries (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    workflow TEXT NOT NULL,
    query TEXT NOT NULL,
    label TEXT,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_saved_queries_user ON saved_queries(user_id);
"""


class LocalRunRepository:
    """SQLite-backed run repository for local development.

    Thread-safe via a per-instance lock. Uses a separate database from
    the workflow cache so concerns stay isolated.
    """

    def __init__(self, db_path: str | Path = "pilot_runs.sqlite"):
        self.db_path = str(db_path)
        self._lock = threading.Lock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(_LOCAL_SCHEMA)
                # Migrate existing databases that lack new columns.
                existing = {
                    row[1]
                    for row in conn.execute("PRAGMA table_info(runs)").fetchall()
                }
                if "duration_ms" not in existing:
                    conn.execute(_MIGRATION_ADD_DURATION)
                if "error_message" not in existing:
                    conn.execute(_MIGRATION_ADD_ERROR)
                if "user_id" not in existing:
                    conn.execute(_MIGRATION_ADD_USER_ID)
                conn.executescript(_SAVED_QUERIES_SCHEMA)
                conn.commit()
            finally:
                conn.close()

    def save(self, record: RunRecord) -> None:
        d = record.to_dict()
        # Convert bool to int for SQLite.
        if d["cache_hit"] is not None:
            d["cache_hit"] = int(d["cache_hit"])
        cols = ", ".join(d.keys())
        placeholders = ", ".join(["?"] * len(d))
        upsert = ", ".join(f"{k}=excluded.{k}" for k in d.keys() if k != "id")
        sql = (
            f"INSERT INTO runs ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {upsert}"
        )
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(sql, list(d.values()))
                conn.commit()
            finally:
                conn.close()

    def get(self, record_id: str) -> Optional[RunRecord]:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM runs WHERE id = ?", (record_id,)
                ).fetchone()
                if row is None:
                    return None
                d = dict(row)
                if d["cache_hit"] is not None:
                    d["cache_hit"] = bool(d["cache_hit"])
                return RunRecord.from_row(d)
            finally:
                conn.close()

    def list_runs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        workflow: Optional[str] = None,
        mode: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[RunRecord]:
        clauses: List[str] = []
        params: List[Any] = []
        if workflow:
            clauses.append("workflow = ?")
            params.append(workflow)
        if mode:
            clauses.append("mode = ?")
            params.append(mode)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if user_id:
            clauses.append("user_id = ?")
            params.append(user_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM runs{where} ORDER BY started_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(sql, params).fetchall()
                results: List[RunRecord] = []
                for row in rows:
                    d = dict(row)
                    if d["cache_hit"] is not None:
                        d["cache_hit"] = bool(d["cache_hit"])
                    results.append(RunRecord.from_row(d))
                return results
            finally:
                conn.close()

    def summary(self) -> Dict[str, Any]:
        """Return aggregate stats over all persisted runs."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT "
                    "  COUNT(*) AS total_runs, "
                    "  SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed, "
                    "  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed, "
                    "  SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) AS cache_hits, "
                    "  AVG(duration_ms) AS avg_duration_ms, "
                    "  MAX(duration_ms) AS max_duration_ms, "
                    "  MIN(started_at) AS earliest_run, "
                    "  MAX(started_at) AS latest_run "
                    "FROM runs"
                ).fetchone()
                totals = dict(row) if row else {}

                # Workflow breakdown.
                wf_rows = conn.execute(
                    "SELECT workflow, COUNT(*) AS count, "
                    "  AVG(duration_ms) AS avg_duration_ms "
                    "FROM runs GROUP BY workflow ORDER BY count DESC"
                ).fetchall()
                by_workflow = [dict(r) for r in wf_rows]

                # Mode breakdown.
                mode_rows = conn.execute(
                    "SELECT mode, COUNT(*) AS count "
                    "FROM runs GROUP BY mode ORDER BY count DESC"
                ).fetchall()
                by_mode = [dict(r) for r in mode_rows]

                # Cost totals from cost_summary JSON.
                cost_rows = conn.execute(
                    "SELECT cost_summary FROM runs "
                    "WHERE cost_summary IS NOT NULL"
                ).fetchall()
                total_spent = 0.0
                for cr in cost_rows:
                    try:
                        cs = json.loads(cr["cost_summary"])
                        total_spent += float(cs.get("spent_usd", 0))
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass

                # Round aggregates.
                for key in ("avg_duration_ms", "max_duration_ms"):
                    if totals.get(key) is not None:
                        totals[key] = round(totals[key], 1)

                return {
                    **totals,
                    "total_spent_usd": round(total_spent, 6),
                    "by_workflow": by_workflow,
                    "by_mode": by_mode,
                }
            finally:
                conn.close()

    def user_summary(self, user_id: str) -> Dict[str, Any]:
        """Return aggregate stats for a single user."""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT "
                    "  COUNT(*) AS total_runs, "
                    "  COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed, "
                    "  COALESCE(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END), 0) AS failed, "
                    "  COALESCE(SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END), 0) AS cache_hits, "
                    "  AVG(duration_ms) AS avg_duration_ms, "
                    "  MAX(duration_ms) AS max_duration_ms, "
                    "  MIN(started_at) AS earliest_run, "
                    "  MAX(started_at) AS latest_run "
                    "FROM runs WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                totals = dict(row) if row else {}
                for key in ("avg_duration_ms", "max_duration_ms"):
                    if totals.get(key) is not None:
                        totals[key] = round(totals[key], 1)

                cost_rows = conn.execute(
                    "SELECT cost_summary FROM runs "
                    "WHERE cost_summary IS NOT NULL AND user_id = ?",
                    (user_id,),
                ).fetchall()
                total_spent = 0.0
                for cr in cost_rows:
                    try:
                        cs = json.loads(cr["cost_summary"])
                        total_spent += float(cs.get("spent_usd", 0))
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass

                wf_rows = conn.execute(
                    "SELECT workflow, COUNT(*) AS count "
                    "FROM runs WHERE user_id = ? "
                    "GROUP BY workflow ORDER BY count DESC",
                    (user_id,),
                ).fetchall()

                return {
                    **totals,
                    "total_spent_usd": round(total_spent, 6),
                    "by_workflow": [dict(r) for r in wf_rows],
                }
            finally:
                conn.close()

    # --- Saved queries ---

    def save_query(self, sq: SavedQuery) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO saved_queries (id, user_id, workflow, query, label, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (sq.id, sq.user_id, sq.workflow, sq.query, sq.label, sq.created_at),
                )
                conn.commit()
            finally:
                conn.close()

    def list_saved_queries(self, user_id: str) -> List[SavedQuery]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT * FROM saved_queries WHERE user_id = ? "
                    "ORDER BY created_at DESC",
                    (user_id,),
                ).fetchall()
                return [
                    SavedQuery(**dict(row))
                    for row in rows
                ]
            finally:
                conn.close()

    def delete_saved_query(self, query_id: str, user_id: str) -> bool:
        """Delete a saved query by ID, scoped to user. Returns True if deleted."""
        with self._lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    "DELETE FROM saved_queries WHERE id = ? AND user_id = ?",
                    (query_id, user_id),
                )
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()


class PostgresRunRepository:
    """Postgres-backed run repository for pilot environments.

    Requires ``psycopg2`` (install via ``pip install psycopg2-binary``).
    Bootstraps the schema on first use.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._schema_ready = False

    def _connect(self):  # type: ignore[no-untyped-def]
        import psycopg2  # type: ignore[import-untyped]
        import psycopg2.extras  # type: ignore[import-untyped]

        conn = psycopg2.connect(self.dsn)
        return conn

    def _ensure_schema(self) -> None:
        if self._schema_ready:
            return
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute("""\
                    CREATE TABLE IF NOT EXISTS runs (
                        id TEXT PRIMARY KEY,
                        request_id TEXT,
                        run_id TEXT,
                        workflow TEXT NOT NULL,
                        mode TEXT NOT NULL DEFAULT 'smoke',
                        status TEXT NOT NULL DEFAULT 'pending',
                        started_at TIMESTAMPTZ,
                        completed_at TIMESTAMPTZ,
                        duration_ms DOUBLE PRECISION,
                        query_preview TEXT,
                        cache_hit BOOLEAN,
                        cost_summary JSONB,
                        artifact_location TEXT,
                        artifact_count INTEGER DEFAULT 0,
                        error_message TEXT,
                        extra JSONB,
                        user_id TEXT
                    );

                    CREATE INDEX IF NOT EXISTS idx_runs_run_id
                        ON runs(run_id);
                    CREATE INDEX IF NOT EXISTS idx_runs_started_at
                        ON runs(started_at DESC);

                    CREATE TABLE IF NOT EXISTS saved_queries (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        workflow TEXT NOT NULL,
                        query TEXT NOT NULL,
                        label TEXT,
                        created_at TIMESTAMPTZ
                    );

                    CREATE INDEX IF NOT EXISTS idx_saved_queries_user
                        ON saved_queries(user_id);
                """)
            conn.commit()
            self._schema_ready = True
        finally:
            conn.close()

    def save(self, record: RunRecord) -> None:
        self._ensure_schema()
        d = record.to_dict()
        # Postgres handles JSONB natively — undo the JSON string encoding.
        for key in ("cost_summary", "extra"):
            if d[key] is not None and isinstance(d[key], str):
                d[key] = json.loads(d[key])

        cols = ", ".join(d.keys())
        placeholders = ", ".join(["%s"] * len(d))
        upsert = ", ".join(
            f"{k}=EXCLUDED.{k}" for k in d.keys() if k != "id"
        )
        sql = (
            f"INSERT INTO runs ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {upsert}"
        )
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, list(d.values()))
            conn.commit()
        finally:
            conn.close()

    def get(self, record_id: str) -> Optional[RunRecord]:
        self._ensure_schema()
        conn = self._connect()
        try:
            import psycopg2.extras  # type: ignore[import-untyped]

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM runs WHERE id = %s", (record_id,))
                row = cur.fetchone()
                if row is None:
                    return None
                d = dict(row)
                # Convert datetime objects to ISO strings.
                for k in ("started_at", "completed_at"):
                    if d[k] is not None and not isinstance(d[k], str):
                        d[k] = d[k].isoformat()
                return RunRecord.from_row(d)
        finally:
            conn.close()

    def list_runs(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        workflow: Optional[str] = None,
        mode: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[RunRecord]:
        self._ensure_schema()
        clauses: List[str] = []
        params: List[Any] = []
        if workflow:
            clauses.append("workflow = %s")
            params.append(workflow)
        if mode:
            clauses.append("mode = %s")
            params.append(mode)
        if status:
            clauses.append("status = %s")
            params.append(status)
        if user_id:
            clauses.append("user_id = %s")
            params.append(user_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM runs{where} ORDER BY started_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        conn = self._connect()
        try:
            import psycopg2.extras  # type: ignore[import-untyped]

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                results: List[RunRecord] = []
                for row in cur.fetchall():
                    d = dict(row)
                    for k in ("started_at", "completed_at"):
                        if d[k] is not None and not isinstance(d[k], str):
                            d[k] = d[k].isoformat()
                    results.append(RunRecord.from_row(d))
                return results
        finally:
            conn.close()

    def summary(self) -> Dict[str, Any]:
        self._ensure_schema()
        conn = self._connect()
        try:
            import psycopg2.extras  # type: ignore[import-untyped]

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT "
                    "  COUNT(*) AS total_runs, "
                    "  SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed, "
                    "  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed, "
                    "  SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) AS cache_hits, "
                    "  AVG(duration_ms) AS avg_duration_ms, "
                    "  MAX(duration_ms) AS max_duration_ms, "
                    "  MIN(started_at) AS earliest_run, "
                    "  MAX(started_at) AS latest_run "
                    "FROM runs"
                )
                totals = dict(cur.fetchone() or {})
                for key in ("avg_duration_ms", "max_duration_ms"):
                    if totals.get(key) is not None:
                        totals[key] = round(float(totals[key]), 1)
                for key in ("earliest_run", "latest_run"):
                    if totals.get(key) is not None and not isinstance(
                        totals[key], str
                    ):
                        totals[key] = totals[key].isoformat()

                cur.execute(
                    "SELECT workflow, COUNT(*) AS count, "
                    "  ROUND(AVG(duration_ms)::numeric, 1) AS avg_duration_ms "
                    "FROM runs GROUP BY workflow ORDER BY count DESC"
                )
                by_workflow = [dict(r) for r in cur.fetchall()]

                cur.execute(
                    "SELECT mode, COUNT(*) AS count "
                    "FROM runs GROUP BY mode ORDER BY count DESC"
                )
                by_mode = [dict(r) for r in cur.fetchall()]

                cur.execute(
                    "SELECT COALESCE("
                    "  SUM((cost_summary->>'spent_usd')::numeric), 0"
                    ") AS total_spent_usd FROM runs "
                    "WHERE cost_summary IS NOT NULL"
                )
                spent_row = cur.fetchone()
                total_spent = float(spent_row["total_spent_usd"]) if spent_row else 0.0

                return {
                    **totals,
                    "total_spent_usd": round(total_spent, 6),
                    "by_workflow": by_workflow,
                    "by_mode": by_mode,
                }
        finally:
            conn.close()

    def user_summary(self, user_id: str) -> Dict[str, Any]:
        self._ensure_schema()
        conn = self._connect()
        try:
            import psycopg2.extras  # type: ignore[import-untyped]

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT "
                    "  COUNT(*) AS total_runs, "
                    "  COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) AS completed, "
                    "  COALESCE(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END), 0) AS failed, "
                    "  COALESCE(SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END), 0) AS cache_hits, "
                    "  AVG(duration_ms) AS avg_duration_ms, "
                    "  MAX(duration_ms) AS max_duration_ms, "
                    "  MIN(started_at) AS earliest_run, "
                    "  MAX(started_at) AS latest_run "
                    "FROM runs WHERE user_id = %s",
                    (user_id,),
                )
                totals = dict(cur.fetchone() or {})
                for key in ("avg_duration_ms", "max_duration_ms"):
                    if totals.get(key) is not None:
                        totals[key] = round(float(totals[key]), 1)
                for key in ("earliest_run", "latest_run"):
                    if totals.get(key) is not None and not isinstance(
                        totals[key], str
                    ):
                        totals[key] = totals[key].isoformat()

                cur.execute(
                    "SELECT COALESCE("
                    "  SUM((cost_summary->>'spent_usd')::numeric), 0"
                    ") AS total_spent_usd FROM runs "
                    "WHERE cost_summary IS NOT NULL AND user_id = %s",
                    (user_id,),
                )
                spent_row = cur.fetchone()
                total_spent = float(spent_row["total_spent_usd"]) if spent_row else 0.0

                cur.execute(
                    "SELECT workflow, COUNT(*) AS count "
                    "FROM runs WHERE user_id = %s "
                    "GROUP BY workflow ORDER BY count DESC",
                    (user_id,),
                )
                by_workflow = [dict(r) for r in cur.fetchall()]

                return {
                    **totals,
                    "total_spent_usd": round(total_spent, 6),
                    "by_workflow": by_workflow,
                }
        finally:
            conn.close()

    def save_query(self, sq: SavedQuery) -> None:
        self._ensure_schema()
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO saved_queries (id, user_id, workflow, query, label, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (sq.id, sq.user_id, sq.workflow, sq.query, sq.label, sq.created_at),
                )
            conn.commit()
        finally:
            conn.close()

    def list_saved_queries(self, user_id: str) -> List[SavedQuery]:
        self._ensure_schema()
        conn = self._connect()
        try:
            import psycopg2.extras  # type: ignore[import-untyped]

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM saved_queries WHERE user_id = %s "
                    "ORDER BY created_at DESC",
                    (user_id,),
                )
                return [SavedQuery(**dict(row)) for row in cur.fetchall()]
        finally:
            conn.close()

    def delete_saved_query(self, query_id: str, user_id: str) -> bool:
        self._ensure_schema()
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM saved_queries WHERE id = %s AND user_id = %s",
                    (query_id, user_id),
                )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Factory functions — read configuration from environment
# ---------------------------------------------------------------------------


def create_artifact_store() -> ArtifactStore:
    """Create an artifact store from environment configuration."""
    backend = os.environ.get("PILOT_ARTIFACT_STORE", "local").strip().lower()

    if backend == "s3":
        bucket = os.environ.get("PILOT_S3_BUCKET", "").strip()
        if not bucket:
            raise RuntimeError(
                "PILOT_S3_BUCKET is required when PILOT_ARTIFACT_STORE=s3"
            )
        prefix = os.environ.get("PILOT_S3_PREFIX", "artifacts/").strip()
        return S3ArtifactStore(bucket=bucket, prefix=prefix)

    return LocalArtifactStore()


def create_run_repository() -> RunRepository:
    """Create a run repository from environment configuration."""
    backend = os.environ.get("PILOT_RUN_STORE", "local").strip().lower()

    if backend == "postgres":
        dsn = os.environ.get("PILOT_POSTGRES_URL", "").strip()
        if not dsn:
            raise RuntimeError(
                "PILOT_POSTGRES_URL is required when PILOT_RUN_STORE=postgres"
            )
        return PostgresRunRepository(dsn=dsn)

    db_path = os.environ.get("PILOT_RUN_STORE_PATH", "pilot_runs.sqlite").strip()
    return LocalRunRepository(db_path=db_path)


# ---------------------------------------------------------------------------
# High-level persistence helper for API endpoints
# ---------------------------------------------------------------------------


def persist_workflow_run(
    *,
    run_repo: RunRepository,
    artifact_store: ArtifactStore,
    workflow: str,
    mode: str,
    request_id: Optional[str],
    payload: Dict[str, Any],
    query_preview: Optional[str] = None,
    artifact_dir: Optional[str] = None,
    started_at: Optional[str] = None,
    duration_ms: Optional[float] = None,
    status: str = "completed",
    error_message: Optional[str] = None,
    user_id: Optional[str] = None,
) -> RunRecord:
    """Create a RunRecord from a completed workflow payload, persist it, and
    optionally upload artifacts. Returns the saved record."""

    run_id = payload.get("run_id")
    summary = payload.get("summary", {})
    cache_hit = payload.get("cache_hit")

    now = _utc_now()
    record = RunRecord(
        request_id=request_id,
        run_id=run_id,
        workflow=workflow,
        mode=mode,
        status=status,
        started_at=started_at or now,
        completed_at=now,
        duration_ms=round(duration_ms, 1) if duration_ms is not None else None,
        query_preview=_query_preview(query_preview),
        cache_hit=cache_hit,
        cost_summary=summary if summary else None,
        error_message=error_message,
        user_id=user_id,
    )

    # Upload artifacts if a directory exists.
    if artifact_dir and run_id and status == "completed":
        art_dir = Path(artifact_dir) / run_id
        if art_dir.is_dir():
            try:
                locations = artifact_store.upload_directory(run_id, art_dir)
                record.artifact_count = len(locations)
                record.artifact_location = str(art_dir)
            except Exception:
                logger.exception("Failed to upload artifacts for run %s", run_id)

    run_repo.save(record)
    logger.info(
        "Persisted run id=%s workflow=%s run_id=%s status=%s duration_ms=%s",
        record.id,
        record.workflow,
        record.run_id,
        record.status,
        record.duration_ms,
    )
    return record
