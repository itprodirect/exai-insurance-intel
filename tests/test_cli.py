from __future__ import annotations

import json

from exa_demo.cli import main
from exa_demo.cache import SqliteCacheStore


def test_search_command_smoke_emits_json_and_artifacts(tmp_path, capsys) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
    artifact_dir = tmp_path / 'artifacts'

    exit_code = main(
        [
            'search',
            'forensic engineer insurance expert witness',
            '--mode',
            'smoke',
            '--run-id',
            'cli-search',
            '--sqlite-path',
            str(sqlite_path),
            '--artifact-dir',
            str(artifact_dir),
            '--json',
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output['run_id'] == 'cli-search'
    assert output['record']['result_count'] == 5
    assert (artifact_dir / 'cli-search' / 'summary.json').exists()


def test_eval_command_smoke_writes_artifacts(tmp_path, capsys) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
    artifact_dir = tmp_path / 'artifacts'

    exit_code = main(
        [
            'eval',
            '--mode',
            'smoke',
            '--run-id',
            'cli-eval',
            '--sqlite-path',
            str(sqlite_path),
            '--artifact-dir',
            str(artifact_dir),
            '--limit',
            '2',
            '--json',
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output['run_id'] == 'cli-eval'
    assert output['summary']['request_count'] == 2
    assert (artifact_dir / 'cli-eval' / 'queries.jsonl').exists()
    assert (artifact_dir / 'cli-eval' / 'results.jsonl').exists()


def test_budget_command_reads_ledger(tmp_path, capsys) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
    cache = SqliteCacheStore(sqlite_path, 24.0)
    cache.ledger_add(
        request_hash='hash-1',
        query='forensic engineer',
        cache_hit=False,
        estimated_cost=0.01,
        actual_cost=0.02,
        run_id='budget-run',
    )

    exit_code = main(['budget', '--sqlite-path', str(sqlite_path), '--run-id', 'budget-run', '--json'])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output['summary']['request_count'] == 1
    assert output['summary']['spent_usd'] == 0.02
    assert output['ledger_rows'] == 1
