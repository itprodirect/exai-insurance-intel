from __future__ import annotations

import json
from pathlib import Path

from exa_demo.client import ExaCallMeta
from exa_demo.config import RuntimeState, default_config, default_pricing
from exa_demo.endpoint_workflows import (
    run_answer_workflow,
    run_find_similar_workflow,
    run_research_workflow,
    run_structured_search_workflow,
)
from exa_demo.ranked_workflows import run_eval_workflow, run_search_workflow


def _smoke_runtime(run_id: str) -> RuntimeState:
    return RuntimeState(exa_api_key='', smoke_no_network=True, run_id=run_id)


def _runtime_metadata(runtime: RuntimeState) -> dict[str, object]:
    return {
        'execution_mode': 'smoke',
        'smoke_no_network': runtime.smoke_no_network,
        'run_id_source': 'explicit',
    }


def _config(tmp_path: Path, *, num_results: int = 5) -> dict[str, object]:
    config = default_config()
    config['sqlite_path'] = str(tmp_path / 'cache.sqlite')
    config['num_results'] = num_results
    return config


def test_run_search_workflow_smoke_writes_ranked_artifacts(tmp_path) -> None:
    runtime = _smoke_runtime('workflow-search')
    config = _config(tmp_path)
    pricing = default_pricing()

    payload, record = run_search_workflow(
        query='forensic engineer insurance expert witness',
        artifact_dir=str(tmp_path / 'artifacts'),
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=_runtime_metadata(runtime),
    )

    summary_path = tmp_path / 'artifacts' / 'workflow-search' / 'summary.json'
    results_path = tmp_path / 'artifacts' / 'workflow-search' / 'results.jsonl'
    summary_payload = json.loads(summary_path.read_text(encoding='utf-8'))
    result_rows = results_path.read_text(encoding='utf-8').strip().splitlines()

    assert payload['run_id'] == 'workflow-search'
    assert payload['record']['request_id'].startswith('smoke-')
    assert payload['taxonomy']['failure_rate'] == 0.0
    assert record.result_count == 5
    assert len(result_rows) == 1
    assert summary_payload['query_records_written'] == 1
    assert summary_payload['extra']['runtime']['execution_mode'] == 'smoke'
    assert summary_payload['extra']['taxonomy']['failure_rate'] == 0.0
    assert summary_payload['qualitative_notes'][-1] == 'Smoke mode active: results are mocked and costs are zero.'


def test_run_eval_workflow_direct_compare_writes_comparison_bundle(tmp_path) -> None:
    runtime = _smoke_runtime('workflow-eval')
    config = _config(tmp_path)
    pricing = default_pricing()
    artifact_dir = tmp_path / 'artifacts'
    baseline_dir = artifact_dir / 'baseline-run'
    baseline_dir.mkdir(parents=True)

    queries_file = tmp_path / 'queries.json'
    queries_file.write_text(json.dumps(['query one', 'query two']), encoding='utf-8')
    baseline_results = [
        {
            'query': 'query one',
            'result_count': 0,
            'relevance_keywords_present': False,
            'linkedin_present': False,
            'resolved_search_type': 'auto',
            'failure_reasons': ['no_results'],
            'primary_failure_reason': 'no_results',
            'confidence_score': 0.0,
        },
        {
            'query': 'query two',
            'result_count': 1,
            'relevance_keywords_present': False,
            'linkedin_present': False,
            'resolved_search_type': 'auto',
            'failure_reasons': ['off_domain', 'low_confidence'],
            'primary_failure_reason': 'off_domain',
            'confidence_score': 0.2,
        },
    ]
    (baseline_dir / 'results.jsonl').write_text(
        '\n'.join(json.dumps(row, sort_keys=True) for row in baseline_results) + '\n',
        encoding='utf-8',
    )
    (baseline_dir / 'summary.json').write_text(
        json.dumps(
            {
                'run_id': 'baseline-run',
                'spent_usd': 0.12,
                'avg_cost_per_uncached_query': 0.06,
                'observed_relevance_rate': 0.0,
                'observed_confidence_score': 0.1,
                'observed_failure_rate': 1.0,
                'extra': {'run_context': {'query_suite': 'all'}},
            },
            indent=2,
            sort_keys=True,
        )
        + '\n',
        encoding='utf-8',
    )

    payload = run_eval_workflow(
        artifact_dir=str(artifact_dir),
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=_runtime_metadata(runtime),
        suite='insurance',
        queries_file=str(queries_file),
        limit=None,
        compare_to_run_id='baseline-run',
        compare_base_dir=str(artifact_dir),
    )

    summary_payload = json.loads((artifact_dir / 'workflow-eval' / 'summary.json').read_text(encoding='utf-8'))

    assert payload['run_id'] == 'workflow-eval'
    assert payload['queries_executed'] == 2
    assert payload['comparison']['baseline_run_id'] == 'baseline-run'
    assert payload['comparison']['candidate_run_id'] == 'workflow-eval'
    assert (artifact_dir / 'workflow-eval' / 'comparison.json').exists()
    assert (artifact_dir / 'workflow-eval' / 'grouped_query_outcomes.csv').exists()
    assert summary_payload['extra']['run_context']['query_suite'] == 'all'
    assert summary_payload['extra']['comparison']['baseline_run_id'] == 'baseline-run'
    assert summary_payload['qualitative_notes'][-1] == 'Smoke mode active: results are mocked and costs are zero.'


def test_run_answer_workflow_smoke_writes_summary_context(tmp_path) -> None:
    runtime = _smoke_runtime('workflow-answer')
    config = _config(tmp_path)
    pricing = default_pricing()

    payload = run_answer_workflow(
        query='What is the Florida appraisal clause dispute process?',
        artifact_dir=str(tmp_path / 'artifacts'),
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=_runtime_metadata(runtime),
    )

    run_dir = tmp_path / 'artifacts' / 'workflow-answer'
    summary_payload = json.loads((run_dir / 'summary.json').read_text(encoding='utf-8'))

    assert payload['workflow'] == 'answer'
    assert payload['citation_count'] == 2
    assert 'Mock answer' in payload['answer']
    assert summary_payload['extra']['workflow'] == 'answer'
    assert summary_payload['extra']['answer']['citation_count'] == 2
    assert summary_payload['qualitative_notes'] == [
        'Answer workflow active: answer text and citations are stored in answer.json.',
        'Smoke mode active: answers are mocked and costs are zero.',
    ]


def test_run_research_workflow_smoke_writes_markdown_and_summary_context(tmp_path) -> None:
    runtime = _smoke_runtime('workflow-research')
    config = _config(tmp_path)
    pricing = default_pricing()

    payload = run_research_workflow(
        query='Summarize the Florida CAT market outlook.',
        artifact_dir=str(tmp_path / 'artifacts'),
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=_runtime_metadata(runtime),
    )

    run_dir = tmp_path / 'artifacts' / 'workflow-research'
    summary_payload = json.loads((run_dir / 'summary.json').read_text(encoding='utf-8'))
    markdown = (run_dir / 'research.md').read_text(encoding='utf-8')

    assert payload['workflow'] == 'research'
    assert payload['citation_count'] == 3
    assert 'Mock research report' in (payload['report'] or '')
    assert '# Research Report' in markdown
    assert summary_payload['extra']['workflow'] == 'research'
    assert summary_payload['extra']['research']['citation_count'] == 3
    assert summary_payload['qualitative_notes'] == [
        'Research workflow active: the response payload is stored in research.json.',
        'Smoke mode active: research reports are mocked and costs are zero.',
    ]
    assert summary_payload['extra']['runtime']['execution_mode'] == 'smoke'


def test_run_find_similar_workflow_smoke_caps_requested_results(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_find_similar(
        url: str,
        *,
        config,
        pricing,
        exa_api_key,
        smoke_no_network,
        run_id,
        cache_store,
        num_results=None,
    ):
        captured['url'] = url
        captured['num_results'] = num_results
        return (
            {
                'requestId': 'req-find-similar',
                'results': [
                    {
                        'title': 'Florida Insurance Litigation Firm',
                        'url': 'https://example.com/florida-insurance-litigation-firm',
                        'snippet': 'Mock result',
                        'score': 0.98,
                    }
                ],
                'costDollars': {'total': 0.0},
            },
            ExaCallMeta(
                cache_hit=False,
                request_hash='hash-find-similar',
                request_payload={'url': url},
                estimated_cost_usd=0.01,
                actual_cost_usd=0.0,
                request_id='req-find-similar',
                resolved_search_type='auto',
                created_at_utc='2026-03-21T00:00:00+00:00',
            ),
        )

    from exa_demo import endpoint_workflows as endpoint_module

    monkeypatch.setattr(endpoint_module, 'exa_find_similar', fake_find_similar)

    runtime = _smoke_runtime('workflow-find-similar')
    config = _config(tmp_path, num_results=10)
    pricing = default_pricing()

    payload = run_find_similar_workflow(
        seed_url='https://www.merlinlawgroup.com/',
        artifact_dir=str(tmp_path / 'artifacts'),
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=_runtime_metadata(runtime),
    )

    summary_payload = json.loads(
        (tmp_path / 'artifacts' / 'workflow-find-similar' / 'summary.json').read_text(encoding='utf-8')
    )

    assert captured['url'] == 'https://www.merlinlawgroup.com/'
    assert captured['num_results'] == 3
    assert payload['result_count'] == 1
    assert payload['top_result']['title'] == 'Florida Insurance Litigation Firm'
    assert summary_payload['extra']['workflow'] == 'find-similar'
    assert summary_payload['extra']['find_similar']['result_count'] == 1


def test_run_structured_search_workflow_smoke_writes_schema_context(tmp_path) -> None:
    runtime = _smoke_runtime('workflow-structured')
    config = _config(tmp_path)
    pricing = default_pricing()
    schema_file = tmp_path / 'structured-schema.json'
    schema_file.write_text(
        json.dumps(
            {
                'title': 'Structured Professionals',
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'role': {'type': 'string'},
                },
            }
        ),
        encoding='utf-8',
    )

    payload = run_structured_search_workflow(
        query='independent adjuster florida catastrophe claims',
        schema_file=str(schema_file),
        artifact_dir=str(tmp_path / 'artifacts'),
        config=config,
        pricing=pricing,
        runtime=runtime,
        runtime_metadata=_runtime_metadata(runtime),
    )

    summary_payload = json.loads((tmp_path / 'artifacts' / 'workflow-structured' / 'summary.json').read_text(encoding='utf-8'))

    assert payload['workflow'] == 'structured-search'
    assert payload['schema_file'] == str(schema_file)
    assert payload['structured_output']['schema_title'] == 'Structured Professionals'
    assert summary_payload['extra']['workflow'] == 'structured-search'
    assert summary_payload['extra']['structured_search']['schema_file'] == str(schema_file)
    assert summary_payload['extra']['structured_search']['structured_keys'] == [
        'field_names',
        'query',
        'record_count',
        'records',
        'schema_title',
    ]
