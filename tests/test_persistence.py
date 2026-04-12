"""Tests for the pilot persistence layer."""

from __future__ import annotations

import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import exa_demo.api as api_module
import exa_demo.persistence as persist_module
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# RunRecord unit tests
# ---------------------------------------------------------------------------


class TestRunRecord:
    def test_defaults(self):
        rec = persist_module.RunRecord(workflow="search", mode="smoke")
        assert rec.status == "pending"
        assert rec.id  # auto-generated
        assert len(rec.id) == 12

    def test_to_dict_serializes_nested(self):
        rec = persist_module.RunRecord(
            workflow="answer",
            mode="smoke",
            cost_summary={"spent_usd": 0.01},
        )
        d = rec.to_dict()
        assert isinstance(d["cost_summary"], str)
        assert json.loads(d["cost_summary"]) == {"spent_usd": 0.01}

    def test_from_row_round_trip(self):
        rec = persist_module.RunRecord(
            workflow="research",
            mode="live",
            cost_summary={"spent_usd": 0.5},
            extra={"note": "test"},
        )
        d = rec.to_dict()
        restored = persist_module.RunRecord.from_row(d)
        assert restored.workflow == "research"
        assert restored.cost_summary == {"spent_usd": 0.5}
        assert restored.extra == {"note": "test"}


# ---------------------------------------------------------------------------
# Query preview helper
# ---------------------------------------------------------------------------


class TestQueryPreview:
    def test_short_query(self):
        assert persist_module._query_preview("hello") == "hello"

    def test_long_query_truncated(self):
        long = "x" * 300
        preview = persist_module._query_preview(long)
        assert len(preview) == 203  # 200 + "..."
        assert preview.endswith("...")

    def test_none_returns_none(self):
        assert persist_module._query_preview(None) is None


# ---------------------------------------------------------------------------
# LocalArtifactStore
# ---------------------------------------------------------------------------


class TestLocalArtifactStore:
    def test_upload_and_list(self, tmp_path):
        store = persist_module.LocalArtifactStore(base_dir=tmp_path / "store")
        source = tmp_path / "source.json"
        source.write_text('{"a": 1}')
        loc = store.upload("run-1", "source.json", source)
        assert Path(loc).exists()
        artifacts = store.list_artifacts("run-1")
        assert len(artifacts) == 1

    def test_upload_directory(self, tmp_path):
        store = persist_module.LocalArtifactStore(base_dir=tmp_path / "store")
        src_dir = tmp_path / "artifacts" / "run-2"
        src_dir.mkdir(parents=True)
        (src_dir / "a.json").write_text("{}")
        (src_dir / "b.json").write_text("{}")
        locs = store.upload_directory("run-2", src_dir)
        assert len(locs) == 2

    def test_upload_missing_file_raises(self, tmp_path):
        store = persist_module.LocalArtifactStore(base_dir=tmp_path / "store")
        with pytest.raises(FileNotFoundError):
            store.upload("run-x", "missing.json", tmp_path / "no.json")

    def test_list_empty_run(self, tmp_path):
        store = persist_module.LocalArtifactStore(base_dir=tmp_path / "store")
        assert store.list_artifacts("nonexistent") == []

    def test_run_location_uses_store_path(self, tmp_path):
        store = persist_module.LocalArtifactStore(base_dir=tmp_path / "store")
        assert store.run_location("run-1") == str(tmp_path / "store" / "run-1")


class _FakeS3Client:
    def __init__(self):
        self.uploads = []

    def upload_file(self, local_path, bucket, key):
        self.uploads.append((local_path, bucket, key))

    def list_objects_v2(self, Bucket, Prefix):  # noqa: N803
        contents = [
            {"Key": key}
            for _, bucket, key in self.uploads
            if bucket == Bucket and key.startswith(Prefix)
        ]
        return {"Contents": contents}


def _iso_utc(year, month, day, hour, minute=0, second=0):
    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        second,
        tzinfo=timezone.utc,
    ).isoformat()


def _to_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class _FakePostgresDb:
    def __init__(self):
        self.runs = {}
        self.saved_queries = {}
        self.connect_calls = []


class _FakePostgresConnection:
    def __init__(self, db):
        self.db = db
        self.commits = 0
        self.closed = False

    def cursor(self, cursor_factory=None):
        return _FakePostgresCursor(self.db, cursor_factory=cursor_factory)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


class _FakePostgresCursor:
    def __init__(self, db, cursor_factory=None):
        self.db = db
        self.cursor_factory = cursor_factory
        self._results = []
        self.rowcount = -1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        params = list(params or [])
        self.rowcount = -1

        if normalized.startswith("CREATE TABLE IF NOT EXISTS runs"):
            self._results = []
            return

        if normalized.startswith("INSERT INTO runs"):
            columns = normalized.split("INSERT INTO runs (", 1)[1].split(
                ") VALUES", 1
            )[0]
            row = dict(zip([col.strip() for col in columns.split(",")], params))
            for key in ("started_at", "completed_at"):
                row[key] = _to_datetime(row.get(key))
            self.db.runs[row["id"]] = row
            self._results = []
            self.rowcount = 1
            return

        if normalized == "SELECT * FROM runs WHERE id = %s":
            row = self.db.runs.get(params[0])
            self._results = [dict(row)] if row is not None else []
            return

        if normalized.startswith("SELECT * FROM runs"):
            filtered = list(self.db.runs.values())
            param_idx = 0
            for field in ("workflow", "mode", "status", "user_id"):
                clause = f"{field} = %s"
                if clause in normalized:
                    filtered = [
                        row for row in filtered if row.get(field) == params[param_idx]
                    ]
                    param_idx += 1
            limit = params[param_idx]
            offset = params[param_idx + 1]
            filtered.sort(
                key=lambda row: row.get("started_at") or datetime.min.replace(
                    tzinfo=timezone.utc
                ),
                reverse=True,
            )
            self._results = [
                dict(row) for row in filtered[offset : offset + limit]
            ]
            return

        if (
            "COUNT(*) AS total_runs" in normalized
            and "FROM runs WHERE user_id = %s" not in normalized
        ):
            self._results = [self._summary_row(self.db.runs.values())]
            return

        if normalized.startswith(
            "SELECT workflow, COUNT(*) AS count, ROUND(AVG(duration_ms)::numeric, 1)"
        ):
            self._results = self._by_workflow_rows(
                self.db.runs.values(),
                include_avg=True,
            )
            return

        if normalized.startswith("SELECT mode, COUNT(*) AS count FROM runs"):
            counts = {}
            for row in self.db.runs.values():
                counts[row["mode"]] = counts.get(row["mode"], 0) + 1
            self._results = [
                {"mode": mode, "count": count}
                for mode, count in sorted(
                    counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ]
            return

        if "SUM((cost_summary->>'spent_usd')::numeric)" in normalized:
            rows = self.db.runs.values()
            if "AND user_id = %s" in normalized:
                rows = [row for row in rows if row.get("user_id") == params[0]]
            total = 0.0
            for row in rows:
                cost_summary = row.get("cost_summary") or {}
                total += float(cost_summary.get("spent_usd", 0) or 0)
            self._results = [{"total_spent_usd": total}]
            return

        if "COUNT(*) AS total_runs" in normalized and "FROM runs WHERE user_id = %s" in normalized:
            rows = [row for row in self.db.runs.values() if row.get("user_id") == params[0]]
            self._results = [self._summary_row(rows)]
            return

        if normalized.startswith(
            "SELECT workflow, COUNT(*) AS count FROM runs WHERE user_id = %s"
        ):
            rows = [row for row in self.db.runs.values() if row.get("user_id") == params[0]]
            self._results = self._by_workflow_rows(rows, include_avg=False)
            return

        if normalized.startswith("INSERT INTO saved_queries"):
            row = {
                "id": params[0],
                "user_id": params[1],
                "workflow": params[2],
                "query": params[3],
                "label": params[4],
                "created_at": _to_datetime(params[5]),
            }
            self.db.saved_queries[row["id"]] = row
            self._results = []
            self.rowcount = 1
            return

        if normalized.startswith("SELECT * FROM saved_queries WHERE user_id = %s"):
            rows = [
                dict(row)
                for row in self.db.saved_queries.values()
                if row["user_id"] == params[0]
            ]
            rows.sort(key=lambda row: row["created_at"], reverse=True)
            self._results = rows
            return

        if normalized.startswith("DELETE FROM saved_queries WHERE id = %s AND user_id = %s"):
            existing = self.db.saved_queries.get(params[0])
            deleted = existing is not None and existing["user_id"] == params[1]
            if deleted:
                del self.db.saved_queries[params[0]]
            self._results = []
            self.rowcount = 1 if deleted else 0
            return

        raise AssertionError(f"Unhandled SQL in fake Postgres cursor: {normalized}")

    def fetchone(self):
        return self._results[0] if self._results else None

    def fetchall(self):
        return list(self._results)

    def _summary_row(self, rows):
        rows = list(rows)
        durations = [row["duration_ms"] for row in rows if row.get("duration_ms") is not None]
        started = [row["started_at"] for row in rows if row.get("started_at") is not None]
        return {
            "total_runs": len(rows),
            "completed": sum(1 for row in rows if row.get("status") == "completed"),
            "failed": sum(1 for row in rows if row.get("status") == "failed"),
            "cache_hits": sum(1 for row in rows if row.get("cache_hit") is True),
            "avg_duration_ms": sum(durations) / len(durations) if durations else None,
            "max_duration_ms": max(durations) if durations else None,
            "earliest_run": min(started) if started else None,
            "latest_run": max(started) if started else None,
        }

    def _by_workflow_rows(self, rows, *, include_avg):
        grouped = {}
        for row in rows:
            workflow = row["workflow"]
            bucket = grouped.setdefault(workflow, {"count": 0, "durations": []})
            bucket["count"] += 1
            if row.get("duration_ms") is not None:
                bucket["durations"].append(row["duration_ms"])
        results = []
        for workflow, bucket in grouped.items():
            entry = {
                "workflow": workflow,
                "count": bucket["count"],
            }
            if include_avg:
                entry["avg_duration_ms"] = (
                    round(sum(bucket["durations"]) / len(bucket["durations"]), 1)
                    if bucket["durations"]
                    else None
                )
            results.append(entry)
        results.sort(key=lambda item: (-item["count"], item["workflow"]))
        return results


@pytest.fixture()
def fake_postgres_repo(monkeypatch):
    db = _FakePostgresDb()
    extras = types.ModuleType("psycopg2.extras")
    extras.RealDictCursor = object
    psycopg2 = types.ModuleType("psycopg2")

    def connect(dsn):
        db.connect_calls.append(dsn)
        return _FakePostgresConnection(db)

    psycopg2.connect = connect
    psycopg2.extras = extras
    monkeypatch.setitem(sys.modules, "psycopg2", psycopg2)
    monkeypatch.setitem(sys.modules, "psycopg2.extras", extras)
    return persist_module.PostgresRunRepository("postgresql://fake"), db


class TestS3ArtifactStore:
    def test_run_location_uses_s3_prefix(self):
        store = persist_module.S3ArtifactStore(
            bucket="pilot-artifacts",
            prefix="runs",
        )
        store._client = _FakeS3Client()
        assert (
            store.run_location("run-1")
            == "s3://pilot-artifacts/runs/run-1/"
        )


# ---------------------------------------------------------------------------
# LocalRunRepository
# ---------------------------------------------------------------------------


class TestLocalRunRepository:
    def test_save_and_get(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        rec = persist_module.RunRecord(
            workflow="search",
            mode="smoke",
            status="completed",
            query_preview="test query",
            cache_hit=True,
            cost_summary={"spent_usd": 0.0},
        )
        repo.save(rec)
        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.workflow == "search"
        assert restored.cache_hit is True
        assert restored.cost_summary == {"spent_usd": 0.0}

    def test_upsert(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        rec = persist_module.RunRecord(
            workflow="answer", mode="smoke", status="pending"
        )
        repo.save(rec)
        rec.status = "completed"
        repo.save(rec)
        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.status == "completed"

    def test_list_runs_ordering(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        for i in range(5):
            rec = persist_module.RunRecord(
                workflow="search",
                mode="smoke",
                started_at=f"2026-03-22T00:0{i}:00Z",
            )
            repo.save(rec)
        runs = repo.list_runs(limit=3)
        assert len(runs) == 3
        # Most recent first.
        assert runs[0].started_at > runs[1].started_at  # type: ignore[operator]

    def test_get_missing_returns_none(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        assert repo.get("nonexistent") is None

    def test_cache_hit_false(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        rec = persist_module.RunRecord(
            workflow="search", mode="smoke", cache_hit=False
        )
        repo.save(rec)
        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.cache_hit is False

    def test_cache_hit_none(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        rec = persist_module.RunRecord(workflow="search", mode="smoke")
        repo.save(rec)
        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.cache_hit is None


# ---------------------------------------------------------------------------
# PostgresRunRepository
# ---------------------------------------------------------------------------


class TestPostgresRunRepository:
    def test_save_and_get(self, fake_postgres_repo):
        repo, _ = fake_postgres_repo
        rec = persist_module.RunRecord(
            workflow="search",
            mode="live",
            status="completed",
            started_at=_iso_utc(2026, 3, 22, 0, 1),
            completed_at=_iso_utc(2026, 3, 22, 0, 2),
            cache_hit=True,
            cost_summary={"spent_usd": 0.015, "provider": "exa"},
            extra={"source": "test"},
        )
        repo.save(rec)

        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.workflow == "search"
        assert restored.mode == "live"
        assert restored.status == "completed"
        assert restored.cache_hit is True
        assert restored.cost_summary == {"spent_usd": 0.015, "provider": "exa"}
        assert restored.extra == {"source": "test"}
        assert restored.started_at == _iso_utc(2026, 3, 22, 0, 1)
        assert restored.completed_at == _iso_utc(2026, 3, 22, 0, 2)

    def test_upsert(self, fake_postgres_repo):
        repo, _ = fake_postgres_repo
        rec = persist_module.RunRecord(
            workflow="answer",
            mode="smoke",
            status="pending",
            cache_hit=False,
            extra={"attempt": 1},
        )
        repo.save(rec)

        rec.status = "completed"
        rec.cache_hit = True
        rec.extra = {"attempt": 2}
        repo.save(rec)

        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.status == "completed"
        assert restored.cache_hit is True
        assert restored.extra == {"attempt": 2}

    def test_list_runs_ordering(self, fake_postgres_repo):
        repo, _ = fake_postgres_repo
        for minute in range(5):
            repo.save(
                persist_module.RunRecord(
                    workflow="search",
                    mode="smoke",
                    started_at=_iso_utc(2026, 3, 22, 0, minute),
                )
            )

        runs = repo.list_runs(limit=3)

        assert [run.started_at for run in runs] == [
            _iso_utc(2026, 3, 22, 0, 4),
            _iso_utc(2026, 3, 22, 0, 3),
            _iso_utc(2026, 3, 22, 0, 2),
        ]

    def test_get_missing_returns_none(self, fake_postgres_repo):
        repo, _ = fake_postgres_repo
        assert repo.get("missing") is None

    def test_summary_with_data(self, fake_postgres_repo):
        repo, _ = fake_postgres_repo
        repo.save(
            persist_module.RunRecord(
                workflow="search",
                mode="smoke",
                status="completed",
                started_at=_iso_utc(2026, 3, 22, 0, 0),
                duration_ms=100.0,
                cache_hit=True,
                cost_summary={"spent_usd": 0.005},
            )
        )
        repo.save(
            persist_module.RunRecord(
                workflow="answer",
                mode="live",
                status="completed",
                started_at=_iso_utc(2026, 3, 22, 1, 0),
                duration_ms=200.0,
                cache_hit=False,
                cost_summary={"spent_usd": 0.01},
            )
        )
        repo.save(
            persist_module.RunRecord(
                workflow="search",
                mode="smoke",
                status="failed",
                started_at=_iso_utc(2026, 3, 22, 2, 0),
                duration_ms=50.0,
            )
        )

        summary = repo.summary()

        assert summary["total_runs"] == 3
        assert summary["completed"] == 2
        assert summary["failed"] == 1
        assert summary["cache_hits"] == 1
        assert summary["total_spent_usd"] == pytest.approx(0.015)
        assert summary["by_workflow"] == [
            {"workflow": "search", "count": 2, "avg_duration_ms": 75.0},
            {"workflow": "answer", "count": 1, "avg_duration_ms": 200.0},
        ]
        assert summary["by_mode"] == [
            {"mode": "smoke", "count": 2},
            {"mode": "live", "count": 1},
        ]

    def test_user_summary(self, fake_postgres_repo):
        repo, _ = fake_postgres_repo
        repo.save(
            persist_module.RunRecord(
                workflow="search",
                mode="smoke",
                status="completed",
                started_at=_iso_utc(2026, 3, 22, 0, 0),
                duration_ms=100.0,
                cache_hit=True,
                cost_summary={"spent_usd": 0.005},
                user_id="user-1",
            )
        )
        repo.save(
            persist_module.RunRecord(
                workflow="answer",
                mode="live",
                status="failed",
                started_at=_iso_utc(2026, 3, 22, 1, 0),
                duration_ms=200.0,
                cost_summary={"spent_usd": 0.02},
                user_id="user-1",
            )
        )
        repo.save(
            persist_module.RunRecord(
                workflow="search",
                mode="smoke",
                status="completed",
                started_at=_iso_utc(2026, 3, 22, 2, 0),
                duration_ms=300.0,
                cost_summary={"spent_usd": 0.03},
                user_id="user-2",
            )
        )

        summary = repo.user_summary("user-1")

        assert summary["total_runs"] == 2
        assert summary["completed"] == 1
        assert summary["failed"] == 1
        assert summary["cache_hits"] == 1
        assert summary["total_spent_usd"] == pytest.approx(0.025)
        assert summary["by_workflow"] == [
            {"workflow": "answer", "count": 1},
            {"workflow": "search", "count": 1},
        ]

    def test_save_and_list_saved_queries(self, fake_postgres_repo):
        repo, _ = fake_postgres_repo
        repo.save_query(
            persist_module.SavedQuery(
                id="sq-1",
                user_id="user-1",
                workflow="search",
                query="first query",
                created_at=_iso_utc(2026, 3, 22, 0, 0),
            )
        )
        repo.save_query(
            persist_module.SavedQuery(
                id="sq-2",
                user_id="user-1",
                workflow="answer",
                query="second query",
                created_at=_iso_utc(2026, 3, 22, 1, 0),
            )
        )
        repo.save_query(
            persist_module.SavedQuery(
                id="sq-3",
                user_id="user-2",
                workflow="search",
                query="other user query",
                created_at=_iso_utc(2026, 3, 22, 2, 0),
            )
        )

        saved = repo.list_saved_queries("user-1")

        assert [query.id for query in saved] == ["sq-2", "sq-1"]
        assert [query.query for query in saved] == ["second query", "first query"]

    def test_delete_saved_query(self, fake_postgres_repo):
        repo, _ = fake_postgres_repo
        repo.save_query(
            persist_module.SavedQuery(
                id="sq-1",
                user_id="user-1",
                workflow="search",
                query="query",
                created_at=_iso_utc(2026, 3, 22, 0, 0),
            )
        )

        deleted = repo.delete_saved_query("sq-1", "user-1")

        assert deleted is True
        assert repo.list_saved_queries("user-1") == []


# ---------------------------------------------------------------------------
# persist_workflow_run integration
# ---------------------------------------------------------------------------


class TestPersistWorkflowRun:
    def test_persist_creates_record(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        store = persist_module.LocalArtifactStore(
            base_dir=tmp_path / "store"
        )
        payload = {
            "run_id": "test-run-123",
            "summary": {"spent_usd": 0.0, "cache_hits": 1},
            "cache_hit": True,
        }
        record = persist_module.persist_workflow_run(
            run_repo=repo,
            artifact_store=store,
            workflow="answer",
            mode="smoke",
            request_id="abc123",
            payload=payload,
            query_preview="What is Florida appraisal?",
        )
        assert record.workflow == "answer"
        assert record.cache_hit is True
        assert record.run_id == "test-run-123"

        restored = repo.get(record.id)
        assert restored is not None
        assert restored.request_id == "abc123"

    def test_persist_uploads_artifacts(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        store = persist_module.LocalArtifactStore(
            base_dir=tmp_path / "store"
        )
        # Create a fake artifact directory.
        art_dir = tmp_path / "experiments" / "run-42"
        art_dir.mkdir(parents=True)
        (art_dir / "config.json").write_text("{}")
        (art_dir / "summary.json").write_text("{}")

        payload = {"run_id": "run-42", "summary": {}}
        record = persist_module.persist_workflow_run(
            run_repo=repo,
            artifact_store=store,
            workflow="search",
            mode="smoke",
            request_id=None,
            payload=payload,
            artifact_dir=str(tmp_path / "experiments"),
        )
        assert record.artifact_count == 2
        assert record.artifact_location == str(tmp_path / "store" / "run-42")

    def test_persist_uploads_artifacts_to_s3_location(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        store = persist_module.S3ArtifactStore(
            bucket="pilot-artifacts",
            prefix="runs",
        )
        store._client = _FakeS3Client()
        art_dir = tmp_path / "experiments" / "run-42"
        art_dir.mkdir(parents=True)
        (art_dir / "config.json").write_text("{}")
        (art_dir / "summary.json").write_text("{}")

        record = persist_module.persist_workflow_run(
            run_repo=repo,
            artifact_store=store,
            workflow="search",
            mode="smoke",
            request_id=None,
            payload={"run_id": "run-42", "summary": {}},
            artifact_dir=str(tmp_path / "experiments"),
        )

        assert record.artifact_count == 2
        assert record.artifact_location == "s3://pilot-artifacts/runs/run-42/"


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


class TestFactories:
    def test_create_artifact_store_local(self, monkeypatch):
        monkeypatch.delenv("PILOT_ARTIFACT_STORE", raising=False)
        store = persist_module.create_artifact_store()
        assert isinstance(store, persist_module.LocalArtifactStore)

    def test_create_artifact_store_s3_success(self, monkeypatch):
        monkeypatch.setenv("PILOT_ARTIFACT_STORE", "s3")
        monkeypatch.setenv("PILOT_S3_BUCKET", "test-bucket")
        store = persist_module.create_artifact_store()
        assert isinstance(store, persist_module.S3ArtifactStore)
        assert store.bucket == "test-bucket"

    def test_create_artifact_store_s3_requires_bucket(self, monkeypatch):
        monkeypatch.setenv("PILOT_ARTIFACT_STORE", "s3")
        monkeypatch.delenv("PILOT_S3_BUCKET", raising=False)
        with pytest.raises(RuntimeError, match="PILOT_S3_BUCKET"):
            persist_module.create_artifact_store()

    def test_create_run_repository_local(self, monkeypatch):
        monkeypatch.delenv("PILOT_RUN_STORE", raising=False)
        repo = persist_module.create_run_repository()
        assert isinstance(repo, persist_module.LocalRunRepository)

    def test_create_run_repository_postgres_success(self, monkeypatch):
        monkeypatch.setenv("PILOT_RUN_STORE", "postgres")
        monkeypatch.setenv("PILOT_POSTGRES_URL", "postgresql://fake")
        repo = persist_module.create_run_repository()
        assert isinstance(repo, persist_module.PostgresRunRepository)
        assert repo.dsn == "postgresql://fake"

    def test_create_run_repository_postgres_requires_url(self, monkeypatch):
        monkeypatch.setenv("PILOT_RUN_STORE", "postgres")
        monkeypatch.delenv("PILOT_POSTGRES_URL", raising=False)
        with pytest.raises(RuntimeError, match="PILOT_POSTGRES_URL"):
            persist_module.create_run_repository()


# ---------------------------------------------------------------------------
# API integration: /api/runs endpoints
# ---------------------------------------------------------------------------


def _make_prepare_context_with_sqlite(sqlite_path):
    def _prepare_context(mode, config_overrides=None):
        from exa_demo.cli_runtime import resolve_runtime, runtime_metadata
        from exa_demo.config import default_config, default_pricing

        config = default_config()
        config["sqlite_path"] = str(sqlite_path)
        pricing = default_pricing()
        if config_overrides:
            config.update(config_overrides)
        runtime = resolve_runtime(mode, run_id=None)
        meta = runtime_metadata(runtime)
        return config, pricing, runtime, meta

    return _prepare_context


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """TestClient with persistence pointed at temp dirs."""
    monkeypatch.setattr(api_module, "ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setattr(
        api_module,
        "_prepare_context",
        _make_prepare_context_with_sqlite(tmp_path / "cache.sqlite"),
    )
    monkeypatch.setattr(
        api_module,
        "run_repo",
        persist_module.LocalRunRepository(db_path=tmp_path / "runs.sqlite"),
    )
    monkeypatch.setattr(
        api_module,
        "artifact_store",
        persist_module.LocalArtifactStore(base_dir=tmp_path / "store"),
    )
    return TestClient(api_module.app)


def test_search_persists_run(client):
    resp = client.post(
        "/api/search", json={"query": "test query", "mode": "smoke"}
    )
    assert resp.status_code == 200

    runs_resp = client.get("/api/runs")
    assert runs_resp.status_code == 200
    data = runs_resp.json()
    assert data["count"] >= 1
    run = data["runs"][0]
    assert run["workflow"] == "search"
    assert run["mode"] == "smoke"
    assert run["status"] == "completed"
    assert run["query_preview"] == "test query"


def test_get_run_by_id(client):
    client.post("/api/search", json={"query": "test", "mode": "smoke"})
    runs = client.get("/api/runs").json()["runs"]
    record_id = runs[0]["id"]

    resp = client.get(f"/api/runs/{record_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == record_id


def test_get_run_not_found(client):
    resp = client.get("/api/runs/nonexistent")
    assert resp.status_code == 404


def test_runs_list_pagination(client):
    for i in range(3):
        client.post(
            "/api/search", json={"query": f"query {i}", "mode": "smoke"}
        )
    resp = client.get("/api/runs?limit=2&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2

    resp2 = client.get("/api/runs?limit=2&offset=2")
    data2 = resp2.json()
    assert data2["count"] == 1


def test_runs_list_rejects_negative_pagination(client):
    for i in range(2):
        client.post(
            "/api/search", json={"query": f"query {i}", "mode": "smoke"}
        )

    resp = client.get("/api/runs?limit=-1&offset=0")
    assert resp.status_code == 400
    assert "Invalid limit" in resp.json()["detail"]

    resp = client.get("/api/runs?limit=2&offset=-1")
    assert resp.status_code == 400
    assert "Invalid offset" in resp.json()["detail"]


def test_answer_persists_run(client):
    client.post(
        "/api/answer",
        json={"query": "What is appraisal?", "mode": "smoke"},
    )
    runs = client.get("/api/runs").json()["runs"]
    answer_runs = [r for r in runs if r["workflow"] == "answer"]
    assert len(answer_runs) == 1
    assert answer_runs[0]["query_preview"] == "What is appraisal?"


# ---------------------------------------------------------------------------
# Duration and timing
# ---------------------------------------------------------------------------


class TestDuration:
    def test_duration_persisted(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        rec = persist_module.RunRecord(
            workflow="search", mode="smoke", duration_ms=123.4
        )
        repo.save(rec)
        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.duration_ms == 123.4

    def test_persist_workflow_run_with_duration(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        store = persist_module.LocalArtifactStore(
            base_dir=tmp_path / "store"
        )
        record = persist_module.persist_workflow_run(
            run_repo=repo,
            artifact_store=store,
            workflow="search",
            mode="smoke",
            request_id=None,
            payload={"run_id": "x", "summary": {}},
            duration_ms=456.78,
        )
        assert record.duration_ms == 456.8  # rounded


class TestErrorMessage:
    def test_error_message_persisted(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        rec = persist_module.RunRecord(
            workflow="search",
            mode="smoke",
            status="failed",
            error_message="Something broke",
        )
        repo.save(rec)
        restored = repo.get(rec.id)
        assert restored is not None
        assert restored.error_message == "Something broke"


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


class TestFiltering:
    def test_filter_by_workflow(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        for wf in ("search", "search", "answer"):
            repo.save(persist_module.RunRecord(workflow=wf, mode="smoke"))
        assert len(repo.list_runs(workflow="search")) == 2
        assert len(repo.list_runs(workflow="answer")) == 1

    def test_filter_by_status(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        repo.save(
            persist_module.RunRecord(
                workflow="search", mode="smoke", status="completed"
            )
        )
        repo.save(
            persist_module.RunRecord(
                workflow="search", mode="smoke", status="failed"
            )
        )
        assert len(repo.list_runs(status="completed")) == 1
        assert len(repo.list_runs(status="failed")) == 1

    def test_filter_by_mode(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        repo.save(
            persist_module.RunRecord(workflow="search", mode="smoke")
        )
        repo.save(
            persist_module.RunRecord(workflow="search", mode="live")
        )
        assert len(repo.list_runs(mode="smoke")) == 1


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class TestSummary:
    def test_summary_empty(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        s = repo.summary()
        assert s["total_runs"] == 0
        assert s["total_spent_usd"] == 0.0

    def test_summary_with_data(self, tmp_path):
        repo = persist_module.LocalRunRepository(
            db_path=tmp_path / "runs.sqlite"
        )
        repo.save(
            persist_module.RunRecord(
                workflow="search",
                mode="smoke",
                status="completed",
                duration_ms=100.0,
                cache_hit=True,
                cost_summary={"spent_usd": 0.005},
            )
        )
        repo.save(
            persist_module.RunRecord(
                workflow="answer",
                mode="smoke",
                status="completed",
                duration_ms=200.0,
                cache_hit=False,
                cost_summary={"spent_usd": 0.01},
            )
        )
        repo.save(
            persist_module.RunRecord(
                workflow="search",
                mode="smoke",
                status="failed",
                duration_ms=50.0,
                error_message="test error",
            )
        )
        s = repo.summary()
        assert s["total_runs"] == 3
        assert s["completed"] == 2
        assert s["failed"] == 1
        assert s["cache_hits"] == 1
        assert s["avg_duration_ms"] is not None
        assert s["total_spent_usd"] == 0.015
        assert len(s["by_workflow"]) == 2
        assert len(s["by_mode"]) == 1


# ---------------------------------------------------------------------------
# API: ops/summary endpoint
# ---------------------------------------------------------------------------


def test_ops_summary_endpoint(client):
    client.post("/api/search", json={"query": "test", "mode": "smoke"})
    resp = client.get("/api/ops/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_runs"] >= 1
    assert data["completed"] >= 1
    assert "by_workflow" in data
    assert "by_mode" in data


def test_search_run_has_duration(client):
    client.post("/api/search", json={"query": "test", "mode": "smoke"})
    runs = client.get("/api/runs").json()["runs"]
    assert runs[0]["duration_ms"] is not None
    assert runs[0]["duration_ms"] > 0


def test_runs_filter_by_workflow(client):
    client.post("/api/search", json={"query": "test", "mode": "smoke"})
    client.post(
        "/api/answer", json={"query": "test question", "mode": "smoke"}
    )
    resp = client.get("/api/runs?workflow=answer")
    data = resp.json()
    assert data["count"] == 1
    assert data["runs"][0]["workflow"] == "answer"
