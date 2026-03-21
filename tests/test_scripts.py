from __future__ import annotations

import importlib.util
import builtins
import json
import sqlite3
import sys
from argparse import Namespace
from pathlib import Path

import nbformat
import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_script_module(module_name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {relative_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_run_notebook_smoke_live_requires_api_key(tmp_path, monkeypatch, capsys) -> None:
    module = _load_script_module('scripts_run_notebook_smoke_test_live', 'scripts/run_notebook_smoke.py')
    fake_repo_root = tmp_path
    fake_script = fake_repo_root / 'scripts' / 'run_notebook_smoke.py'
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text('# test script placeholder\n', encoding='utf-8')
    (fake_repo_root / 'exa_people_search_eval.ipynb').write_text('{}\n', encoding='utf-8')

    monkeypatch.setattr(module, '__file__', str(fake_script))
    monkeypatch.setattr(module, 'parse_args', lambda: Namespace(mode='live', timeout=5))
    monkeypatch.delenv('EXA_API_KEY', raising=False)

    exit_code = module.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert 'Mode=live requested but EXA_API_KEY is missing.' in captured.err
    assert module.os.environ['EXA_SMOKE_NO_NETWORK'] == '0'


def test_run_notebook_smoke_auto_falls_back_to_smoke(tmp_path, monkeypatch, capsys) -> None:
    module = _load_script_module('scripts_run_notebook_smoke_test_auto', 'scripts/run_notebook_smoke.py')
    fake_repo_root = tmp_path
    fake_script = fake_repo_root / 'scripts' / 'run_notebook_smoke.py'
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text('# test script placeholder\n', encoding='utf-8')
    (fake_repo_root / 'exa_people_search_eval.ipynb').write_text('{}\n', encoding='utf-8')

    runtime_dir = fake_repo_root / 'runtime'
    ipython_dir = fake_repo_root / 'ipython'
    runtime_dir.mkdir()
    ipython_dir.mkdir()

    executed = {}

    class FakeNotebookClient:
        def __init__(self, nb, timeout, kernel_name, resources, allow_errors) -> None:
            executed['nb'] = nb
            executed['timeout'] = timeout
            executed['kernel_name'] = kernel_name
            executed['resources'] = resources
            executed['allow_errors'] = allow_errors

        def execute(self) -> None:
            executed['called'] = True

    monkeypatch.setattr(module, '__file__', str(fake_script))
    monkeypatch.setattr(module, 'parse_args', lambda: Namespace(mode='auto', timeout=17))
    monkeypatch.delenv('EXA_API_KEY', raising=False)
    monkeypatch.setattr(module.tempfile, 'mkdtemp', lambda prefix: str(runtime_dir if 'jupyter' in prefix else ipython_dir))
    monkeypatch.setattr(module.nbformat, 'read', lambda _handle, as_version: nbformat.v4.new_notebook())
    monkeypatch.setattr(module, 'NotebookClient', FakeNotebookClient)

    exit_code = module.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert 'Mode=smoke: EXA_SMOKE_NO_NETWORK=1 (no network/API billing).' in captured.out
    assert 'Notebook execution completed successfully.' in captured.out
    assert module.os.environ['EXA_SMOKE_NO_NETWORK'] == '1'
    assert module.os.environ['JUPYTER_PLATFORM_DIRS'] == '1'
    assert executed['called'] is True
    assert executed['timeout'] == 17
    assert executed['kernel_name'] == 'python3'
    assert executed['allow_errors'] is False
    assert executed['resources']['metadata']['path'] == str(fake_repo_root)


def test_reset_cache_missing_file_exits_cleanly(tmp_path, monkeypatch, capsys) -> None:
    module = _load_script_module('scripts_reset_cache_test_missing', 'scripts/reset_cache.py')
    fake_repo_root = tmp_path
    fake_script = fake_repo_root / 'scripts' / 'reset_cache.py'
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text('# test script placeholder\n', encoding='utf-8')

    monkeypatch.setattr(module, '__file__', str(fake_script))
    monkeypatch.setattr(module.argparse.ArgumentParser, 'parse_args', lambda self: Namespace(yes=True))

    exit_code = module.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert 'No cache file found' in captured.out


def test_reset_cache_cancel_keeps_valid_sqlite_file(tmp_path, monkeypatch, capsys) -> None:
    module = _load_script_module('scripts_reset_cache_test_cancel', 'scripts/reset_cache.py')
    fake_repo_root = tmp_path
    fake_script = fake_repo_root / 'scripts' / 'reset_cache.py'
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text('# test script placeholder\n', encoding='utf-8')
    cache_path = fake_repo_root / 'exa_cache.sqlite'
    with sqlite3.connect(cache_path):
        pass

    monkeypatch.setattr(module, '__file__', str(fake_script))
    monkeypatch.setattr(module.argparse.ArgumentParser, 'parse_args', lambda self: Namespace(yes=False))
    monkeypatch.setattr(builtins, 'input', lambda _prompt: 'no')

    exit_code = module.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert 'Cancelled.' in captured.out
    assert cache_path.exists()


def test_reset_cache_rejects_non_sqlite_file(tmp_path, monkeypatch, capsys) -> None:
    module = _load_script_module('scripts_reset_cache_test_bad_sqlite', 'scripts/reset_cache.py')
    fake_repo_root = tmp_path
    fake_script = fake_repo_root / 'scripts' / 'reset_cache.py'
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text('# test script placeholder\n', encoding='utf-8')
    cache_path = fake_repo_root / 'exa_cache.sqlite'
    cache_path.write_text('not a sqlite database', encoding='utf-8')

    class FakeConnection:
        def __enter__(self):
            raise sqlite3.DatabaseError('file is not a database')

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    monkeypatch.setattr(module, '__file__', str(fake_script))
    monkeypatch.setattr(module.argparse.ArgumentParser, 'parse_args', lambda self: Namespace(yes=True))
    monkeypatch.setattr(module.sqlite3, 'connect', lambda _path: FakeConnection())

    exit_code = module.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert 'did not open cleanly as sqlite' in captured.out
    assert 'Refusing to delete automatically.' in captured.out
    assert cache_path.exists()


def test_run_live_validation_live_requires_api_key(tmp_path, monkeypatch, capsys) -> None:
    module = _load_script_module('scripts_run_live_validation_test_live', 'scripts/run_live_validation.py')
    fake_repo_root = tmp_path
    fake_script = fake_repo_root / 'scripts' / 'run_live_validation.py'
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text('# test script placeholder\n', encoding='utf-8')

    monkeypatch.setattr(module, '__file__', str(fake_script))
    monkeypatch.setattr(
        module,
        'parse_args',
        lambda: Namespace(mode='live', artifact_dir='live-validation-artifacts', run_id_prefix=None, include_comparison=False),
    )
    monkeypatch.delenv('EXA_API_KEY', raising=False)

    exit_code = module.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert 'Mode=live requested but EXA_API_KEY is missing.' in captured.err


def test_run_live_validation_smoke_writes_summary(tmp_path, monkeypatch, capsys) -> None:
    module = _load_script_module('scripts_run_live_validation_test_smoke', 'scripts/run_live_validation.py')
    fake_repo_root = tmp_path
    fake_script = fake_repo_root / 'scripts' / 'run_live_validation.py'
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text('# test script placeholder\n', encoding='utf-8')
    assets_dir = fake_repo_root / 'assets'
    assets_dir.mkdir()
    (assets_dir / 'live_validation_schema.json').write_text('{"type":"object"}\n', encoding='utf-8')

    calls = []

    class FakeCompletedProcess:
        def __init__(self, stdout: str) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ''

    def fake_run(argv, cwd, capture_output, text, check, env):
        calls.append({'argv': argv, 'cwd': cwd, 'env': env})
        command_name = argv[3]
        run_id_map = {
            'search': 'test-prefix-search',
            'answer': 'test-prefix-answer',
            'research': 'test-prefix-research',
            'structured-search': 'test-prefix-structured',
            'find-similar': 'test-prefix-find-similar',
            'compare-search-types': 'test-prefix-compare',
        }
        run_id = run_id_map[command_name]
        run_dir = fake_repo_root / 'live-validation-artifacts' / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / 'summary.json').write_text('{}\n', encoding='utf-8')
        payload = {'workflow': command_name}

        if command_name == 'search':
            (run_dir / 'results.jsonl').write_text('{}\n', encoding='utf-8')
            payload.update(
                {
                    'run_id': run_id,
                    'artifact_dir': str(run_dir),
                    'request_id': f'req-{command_name}',
                    'record': {'query': 'demo'},
                    'summary': {'spent_usd': 0.0},
                }
            )
        elif command_name == 'answer':
            (run_dir / 'answer.json').write_text('{}\n', encoding='utf-8')
            payload.update(
                {
                    'run_id': run_id,
                    'artifact_dir': str(run_dir),
                    'request_id': f'req-{command_name}',
                    'answer': 'Mock answer',
                    'citation_count': 2,
                    'summary': {'spent_usd': 0.0},
                }
            )
        elif command_name == 'research':
            (run_dir / 'research.json').write_text('{}\n', encoding='utf-8')
            (run_dir / 'research.md').write_text('# Research Report\n', encoding='utf-8')
            payload.update(
                {
                    'run_id': run_id,
                    'artifact_dir': str(run_dir),
                    'request_id': f'req-{command_name}',
                    'report': 'Mock research report',
                    'citation_count': 2,
                    'summary': {'spent_usd': 0.0},
                }
            )
        elif command_name == 'structured-search':
            (run_dir / 'structured_output.json').write_text('{}\n', encoding='utf-8')
            payload.update(
                {
                    'run_id': run_id,
                    'artifact_dir': str(run_dir),
                    'request_id': f'req-{command_name}',
                    'structured_output': {'records': []},
                    'summary': {'spent_usd': 0.0},
                }
            )
        elif command_name == 'find-similar':
            (run_dir / 'find_similar.json').write_text('{}\n', encoding='utf-8')
            payload.update(
                {
                    'run_id': run_id,
                    'artifact_dir': str(run_dir),
                    'request_id': f'req-{command_name}',
                    'result_count': 1,
                    'summary': {'spent_usd': 0.0},
                }
            )
        else:
            baseline_dir = fake_repo_root / 'live-validation-artifacts' / 'test-prefix-compare-deep'
            candidate_dir = fake_repo_root / 'live-validation-artifacts' / 'test-prefix-compare-deep-reasoning'
            baseline_dir.mkdir(parents=True, exist_ok=True)
            candidate_dir.mkdir(parents=True, exist_ok=True)
            (baseline_dir / 'summary.json').write_text('{}\n', encoding='utf-8')
            (baseline_dir / 'results.jsonl').write_text('{}\n', encoding='utf-8')
            (candidate_dir / 'summary.json').write_text('{}\n', encoding='utf-8')
            (candidate_dir / 'comparison.json').write_text('{}\n', encoding='utf-8')
            (candidate_dir / 'comparison.md').write_text('# Comparison\n', encoding='utf-8')
            payload = {
                'workflow': 'compare-search-types',
                'base_run_id': run_id,
                'baseline_run': {
                    'run_id': 'test-prefix-compare-deep',
                    'artifact_dir': str(baseline_dir),
                },
                'candidate_run': {
                    'run_id': 'test-prefix-compare-deep-reasoning',
                    'artifact_dir': str(candidate_dir),
                },
                'comparison': {'deltas': {}},
                'comparison_markdown_path': str(candidate_dir / 'comparison.md'),
            }
        return FakeCompletedProcess(json.dumps(payload))

    monkeypatch.setattr(module, '__file__', str(fake_script))
    monkeypatch.setattr(
        module,
        'parse_args',
        lambda: Namespace(mode='smoke', artifact_dir='live-validation-artifacts', run_id_prefix='test-prefix', include_comparison=True),
    )
    monkeypatch.setattr(module.subprocess, 'run', fake_run)
    monkeypatch.delenv('EXA_API_KEY', raising=False)

    exit_code = module.main()
    captured = capsys.readouterr()
    summary_path = fake_repo_root / 'live-validation-artifacts' / 'validation_summary.json'
    summary_payload = json.loads(summary_path.read_text(encoding='utf-8'))

    assert exit_code == 0
    assert 'Mode=smoke: EXA_SMOKE_NO_NETWORK=1 (no network/API billing).' in captured.out
    assert len(calls) == 6
    assert calls[0]['cwd'] == fake_repo_root
    assert summary_payload['mode'] == 'smoke'
    assert summary_payload['run_id_prefix'] == 'test-prefix'
    assert summary_payload['commands'][0]['name'] == 'search'
    assert summary_payload['commands'][0]['request_id_present'] is True
    assert summary_payload['commands'][0]['validated_artifacts']
    assert summary_payload['commands'][-1]['name'] == 'compare-search-types'
    assert any(path.endswith('comparison.md') for path in summary_payload['commands'][-1]['validated_artifacts'])


def test_run_live_validation_live_requires_request_ids_for_single_workflows(
    tmp_path, monkeypatch
) -> None:
    module = _load_script_module(
        'scripts_run_live_validation_test_request_id',
        'scripts/run_live_validation.py',
    )
    fake_repo_root = tmp_path
    fake_script = fake_repo_root / 'scripts' / 'run_live_validation.py'
    fake_script.parent.mkdir(parents=True)
    fake_script.write_text('# test script placeholder\n', encoding='utf-8')
    assets_dir = fake_repo_root / 'assets'
    assets_dir.mkdir()
    (assets_dir / 'live_validation_schema.json').write_text('{"type":"object"}\n', encoding='utf-8')

    class FakeCompletedProcess:
        def __init__(self, stdout: str) -> None:
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ''

    def fake_run(argv, cwd, capture_output, text, check, env):
        command_name = argv[3]
        run_dir = fake_repo_root / 'live-validation-artifacts' / f'live-check-{command_name}'
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / 'summary.json').write_text('{}\n', encoding='utf-8')
        (run_dir / 'results.jsonl').write_text('{}\n', encoding='utf-8')
        payload = {
            'workflow': 'search',
            'run_id': 'live-check-search',
            'artifact_dir': str(run_dir),
            'record': {'query': 'demo'},
            'summary': {'spent_usd': 0.0},
        }
        return FakeCompletedProcess(json.dumps(payload))

    monkeypatch.setattr(module, '__file__', str(fake_script))
    monkeypatch.setattr(
        module,
        'parse_args',
        lambda: Namespace(mode='live', artifact_dir='live-validation-artifacts', run_id_prefix='live-check', include_comparison=False),
    )
    monkeypatch.setattr(module.subprocess, 'run', fake_run)
    monkeypatch.setenv('EXA_API_KEY', 'test-key')

    with pytest.raises(RuntimeError, match='missing request_id'):
        module.main()


def test_build_validation_commands_includes_smoke_workflows(tmp_path) -> None:
    module = _load_script_module('scripts_run_live_validation_test_builder', 'scripts/run_live_validation.py')
    artifact_dir = tmp_path / 'live-validation-artifacts'

    commands = module.build_validation_commands(
        repo_root=tmp_path,
        artifact_dir=artifact_dir,
        run_id_prefix='ci-smoke',
        mode='smoke',
        include_comparison=False,
    )

    assert [command['name'] for command in commands] == [
        'search',
        'answer',
        'research',
        'structured-search',
        'find-similar',
    ]
    assert commands[0]['argv'][-3:] == ['--artifact-dir', str(artifact_dir), '--json']
    assert '--include-comparison' not in ' '.join(str(part) for part in commands[-1]['argv'])
