from __future__ import annotations

import json

import pytest

from exa_demo.cache import SqliteCacheStore
from exa_demo.cli import _apply_search_overrides, build_parser, main


DEPRECATED_REQUEST_FIELDS = {
    'livecrawl',
    'highlightsPerUrl',
    'numSentences',
    'startCrawlDate',
    'endCrawlDate',
}


def assert_no_deprecated_request_fields(value) -> None:
    if isinstance(value, dict):
        assert DEPRECATED_REQUEST_FIELDS.isdisjoint(value)
        for item in value.values():
            assert_no_deprecated_request_fields(item)
    elif isinstance(value, list):
        for item in value:
            assert_no_deprecated_request_fields(item)


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
    assert 'taxonomy' in output
    assert output['record']['request_payload']['contents']['highlights'] == {'maxCharacters': 2666}
    assert_no_deprecated_request_fields(output['record']['request_payload'])
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
    assert 'taxonomy' in output
    summary_payload = json.loads((artifact_dir / 'cli-eval' / 'summary.json').read_text(encoding='utf-8'))
    assert summary_payload['extra']['run_context']['query_suite'] == 'all'
    assert summary_payload['extra']['runtime']['execution_mode'] == 'smoke'
    query_payload = json.loads((artifact_dir / 'cli-eval' / 'queries.jsonl').read_text(encoding='utf-8').splitlines()[0])
    assert query_payload['request_payload']['contents']['highlights'] == {'maxCharacters': 2666}
    assert_no_deprecated_request_fields(query_payload['request_payload'])
    assert (artifact_dir / 'cli-eval' / 'queries.jsonl').exists()
    assert (artifact_dir / 'cli-eval' / 'results.jsonl').exists()
    assert (artifact_dir / 'cli-eval' / 'results.csv').exists()
    manifest_payload = json.loads((artifact_dir / 'cli-eval' / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest_payload['runtime']['execution_mode'] == 'smoke'
    assert {item['filename'] for item in manifest_payload['artifacts']} >= {
        'config.json',
        'queries.jsonl',
        'results.jsonl',
        'results.csv',
        'summary.json',
    }


def test_eval_command_can_emit_before_after_comparison(tmp_path, capsys) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
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

    exit_code = main(
        [
            'eval',
            '--mode',
            'smoke',
            '--run-id',
            'cli-eval-compare',
            '--sqlite-path',
            str(sqlite_path),
            '--artifact-dir',
            str(artifact_dir),
            '--queries-file',
            str(queries_file),
            '--compare-to-run-id',
            'baseline-run',
            '--json',
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output['comparison']['baseline_run_id'] == 'baseline-run'
    assert output['comparison']['candidate_run_id'] == 'cli-eval-compare'
    assert output['comparison']['shared_query_count'] == 2
    assert 'deltas' in output['comparison']
    assert output['comparison']['comparison_context']['group_columns'] == ['query_suite']
    assert output['comparison']['grouped_query_outcomes'][0]['group']['query_suite'] == 'all'
    assert output['comparison']['grouped_query_outcomes'][0]['baseline_resolved_search_type'] == 'auto'
    assert output['comparison']['grouped_query_outcomes'][0]['candidate_resolved_search_type'] == 'auto'
    assert (artifact_dir / 'cli-eval-compare' / 'comparison.md').exists()
    assert (artifact_dir / 'cli-eval-compare' / 'comparison.json').exists()
    assert (artifact_dir / 'cli-eval-compare' / 'grouped_query_outcomes.csv').exists()
    assert output['comparison_markdown_path'].endswith('comparison.md')


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


def test_search_command_live_requires_api_key(tmp_path, monkeypatch) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
    artifact_dir = tmp_path / 'artifacts'

    # Prevent .env contents from re-populating EXA_API_KEY during the test.
    from exa_demo import cli as cli_module

    monkeypatch.setattr(cli_module, 'load_dotenv', lambda: None)
    monkeypatch.delenv('EXA_API_KEY', raising=False)

    with pytest.raises(RuntimeError, match='Missing EXA_API_KEY'):
        main(
            [
                'search',
                'forensic engineer insurance expert witness',
                '--mode',
                'live',
                '--sqlite-path',
                str(sqlite_path),
                '--artifact-dir',
                str(artifact_dir),
            ]
        )


def test_eval_command_rejects_invalid_queries_file(tmp_path) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
    artifact_dir = tmp_path / 'artifacts'
    bad_queries_file = tmp_path / 'queries.json'
    bad_queries_file.write_text('not valid json', encoding='utf-8')

    with pytest.raises(json.JSONDecodeError):
        main(
            [
                'eval',
                '--mode',
                'smoke',
                '--run-id',
                'cli-eval-invalid',
                '--sqlite-path',
                str(sqlite_path),
                '--artifact-dir',
                str(artifact_dir),
                '--queries-file',
                str(bad_queries_file),
            ]
        )


def test_search_parser_accepts_additive_deep_controls() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            'search',
            'forensic engineer insurance expert witness',
            '--additional-query',
            'licensed public adjuster Florida',
            '--additional-query',
            '  catastrophe claims expert witness  ',
            '--start-published-date',
            '2026-01-01',
            '--end-published-date',
            '2026-03-01',
            '--livecrawl',
            '--deep-search-cost-1-25',
            '0.012',
            '--deep-reasoning-search-cost-1-10',
            '0.015',
            '--content-summary-cost',
            '0.002',
        ]
    )

    assert args.additional_queries == [
        'licensed public adjuster Florida',
        '  catastrophe claims expert witness  ',
    ]
    assert args.start_published_date == '2026-01-01'
    assert args.end_published_date == '2026-03-01'
    assert args.livecrawl is True
    assert args.freshness == 'default'
    assert args.max_age_hours is None
    assert args.deep_search_cost_1_10 == 0.012
    assert args.deep_reasoning_search_cost_1_10 == 0.015
    assert args.content_summary_cost == 0.002


def test_search_parser_accepts_freshness_controls() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            'search',
            'forensic engineer insurance expert witness',
            '--freshness',
            'near-real-time',
            '--max-age-hours',
            '6',
        ]
    )

    assert args.freshness == 'near-real-time'
    assert args.max_age_hours == 6


def test_structured_search_parser_accepts_schema_file() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            'structured-search',
            'independent adjuster florida catastrophe claims',
            '--schema-file',
            'schema.json',
        ]
    )

    assert args.command == 'structured-search'
    assert args.schema_file == 'schema.json'
    assert args.search_type == 'deep'


def test_find_similar_parser_accepts_seed_url() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            'find-similar',
            'https://www.merlinlawgroup.com/',
        ]
    )

    assert args.command == 'find-similar'
    assert args.url == 'https://www.merlinlawgroup.com/'
    assert args.search_type == 'deep'


def test_research_parser_accepts_query() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            'research',
            'Summarize the Florida CAT market outlook.',
        ]
    )

    assert args.command == 'research'
    assert args.query == 'Summarize the Florida CAT market outlook.'


def test_answer_parser_accepts_pricing_overrides() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            'answer',
            'What is the Florida appraisal clause dispute process?',
            '--answer-cost',
            '0.006',
        ]
    )

    assert args.command == 'answer'
    assert args.answer_cost == 0.006


def test_apply_search_overrides_maps_additive_controls_and_pricing() -> None:
    from exa_demo.config import default_config, default_pricing

    config = default_config()
    pricing = default_pricing()
    args = build_parser().parse_args(
        [
            'search',
            'forensic engineer insurance expert witness',
            '--additional-query',
            'licensed public adjuster Florida',
            '--additional-query',
            '  catastrophe claims expert witness  ',
            '--start-published-date',
            '2026-01-01',
            '--end-published-date',
            '2026-03-01',
            '--livecrawl',
            '--standard-search-cost-1-10',
            '0.006',
            '--standard-search-additional-result-cost',
            '0.002',
            '--deep-search-cost-1-10',
            '0.012',
            '--deep-search-additional-result-cost',
            '0.003',
            '--deep-reasoning-search-cost-1-10',
            '0.015',
            '--deep-reasoning-search-additional-result-cost',
            '0.004',
            '--answer-cost',
            '0.0055',
            '--find-similar-cost-1-10',
            '0.008',
            '--find-similar-additional-result-cost',
            '0.0025',
            '--content-summary-cost',
            '0.0045',
        ]
    )

    _apply_search_overrides(config, pricing, args)

    assert config['additional_queries'] == [
        'licensed public adjuster Florida',
        'catastrophe claims expert witness',
    ]
    assert config['start_published_date'] == '2026-01-01'
    assert config['end_published_date'] == '2026-03-01'
    assert config['max_age_hours'] == 0
    assert pricing['standard_search_1_10'] == 0.006
    assert pricing['standard_search_additional_result'] == 0.002
    assert pricing['deep_search_1_10'] == 0.012
    assert pricing['deep_search_additional_result'] == 0.003
    assert pricing['deep_reasoning_search_1_10'] == 0.015
    assert pricing['deep_reasoning_search_additional_result'] == 0.004
    assert pricing['answer'] == 0.0055
    assert pricing['find_similar_1_10'] == 0.008
    assert pricing['find_similar_additional_result'] == 0.0025
    assert pricing['content_summary_per_page'] == 0.0045


@pytest.mark.parametrize(
    ('search_type', 'flag', 'legacy_key', 'override_cost'),
    [
        ('auto', '--search-cost-26-100', 'search_26_100', 0.123),
        ('deep', '--deep-search-cost-26-100', 'deep_search_26_100', 0.234),
        (
            'deep-reasoning',
            '--deep-reasoning-search-cost-26-100',
            'deep_reasoning_search_26_100',
            0.345,
        ),
    ],
)
def test_cli_legacy_26_100_pricing_overrides_affect_high_result_estimates(
    search_type: str, flag: str, legacy_key: str, override_cost: float
) -> None:
    from exa_demo.config import default_config, default_pricing
    from exa_demo.cost_model import estimate_unit_cost_for_config

    baseline_config = default_config()
    baseline_config['num_results'] = 30
    baseline_config['search_type'] = search_type
    baseline = estimate_unit_cost_for_config(baseline_config, default_pricing())

    config = default_config()
    pricing = default_pricing()
    args = build_parser().parse_args(
        [
            'search',
            'forensic engineer insurance expert witness',
            '--num-results',
            '30',
            '--type',
            search_type,
            flag,
            str(override_cost),
        ]
    )

    _apply_search_overrides(config, pricing, args)

    assert pricing[legacy_key] == override_cost
    assert estimate_unit_cost_for_config(config, pricing) == override_cost
    assert override_cost != baseline


@pytest.mark.parametrize(
    ('freshness', 'expected_max_age_hours'),
    [
        ('default', None),
        ('cache-only', -1),
        ('daily', 24),
        ('near-real-time', 1),
        ('always-live', 0),
    ],
)
def test_apply_search_overrides_maps_freshness_choices(
    freshness: str, expected_max_age_hours: int | None
) -> None:
    from exa_demo.config import default_config, default_pricing

    config = default_config()
    pricing = default_pricing()
    args = build_parser().parse_args(
        [
            'search',
            'forensic engineer insurance expert witness',
            '--freshness',
            freshness,
        ]
    )

    _apply_search_overrides(config, pricing, args)

    assert config['max_age_hours'] == expected_max_age_hours


def test_apply_search_overrides_prefers_explicit_max_age_hours() -> None:
    from exa_demo.config import default_config, default_pricing

    pricing = default_pricing()
    config = default_config()
    args = build_parser().parse_args(
        [
            'search',
            'forensic engineer insurance expert witness',
            '--freshness',
            'near-real-time',
            '--max-age-hours',
            '6',
        ]
    )

    _apply_search_overrides(config, pricing, args)

    assert config['max_age_hours'] == 6


def test_eval_parser_accepts_named_benchmark_suite() -> None:
    parser = build_parser()
    args = parser.parse_args(['eval', '--suite', 'forensic_and_damage_engineering'])

    assert args.suite == 'forensic_and_damage_engineering'


def test_compare_search_types_command_smoke_emits_comparison_bundle(tmp_path, capsys) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
    artifact_dir = tmp_path / 'artifacts'

    exit_code = main(
        [
            'compare-search-types',
            '--mode',
            'smoke',
            '--run-id',
            'compare-types',
            '--sqlite-path',
            str(sqlite_path),
            '--artifact-dir',
            str(artifact_dir),
            '--suite',
            'forensic_and_damage_engineering',
            '--limit',
            '2',
            '--baseline-type',
            'deep',
            '--candidate-type',
            'deep-reasoning',
            '--json',
        ]
    )

    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output['workflow'] == 'compare-search-types'
    assert output['baseline_search_type'] == 'deep'
    assert output['candidate_search_type'] == 'deep-reasoning'
    assert output['query_suite'] == 'forensic_and_damage_engineering'
    assert output['baseline_run']['run_id'] == 'compare-types-deep'
    assert output['candidate_run']['run_id'] == 'compare-types-deep-reasoning'
    assert output['comparison']['comparison_context']['baseline']['query_suite'] == 'forensic_and_damage_engineering'
    assert output['comparison']['comparison_context']['candidate']['query_suite'] == 'forensic_and_damage_engineering'
    assert output['comparison']['comparison_context']['baseline_resolved_search_type'] == 'deep'
    assert output['comparison']['comparison_context']['candidate_resolved_search_type'] == 'deep-reasoning'
    assert (artifact_dir / 'compare-types-deep' / 'summary.json').exists()
    assert (artifact_dir / 'compare-types-deep-reasoning' / 'comparison.md').exists()


def test_compare_search_types_command_rejects_duplicate_types(tmp_path) -> None:
    with pytest.raises(ValueError, match='must differ'):
        main(
            [
                'compare-search-types',
                '--mode',
                'smoke',
                '--run-id',
                'compare-types',
                '--sqlite-path',
                str(tmp_path / 'cache.sqlite'),
                '--artifact-dir',
                str(tmp_path / 'artifacts'),
                '--baseline-type',
                'deep',
                '--candidate-type',
                'deep',
            ]
        )


def test_answer_command_smoke_emits_json_and_artifact(tmp_path, capsys) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
    artifact_dir = tmp_path / 'artifacts'

    exit_code = main(
        [
            'answer',
            'What is the Florida appraisal clause dispute process?',
            '--mode',
            'smoke',
            '--run-id',
            'answer-run',
            '--sqlite-path',
            str(sqlite_path),
            '--artifact-dir',
            str(artifact_dir),
            '--json',
        ]
    )

    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output['workflow'] == 'answer'
    assert output['run_id'] == 'answer-run'
    assert output['citation_count'] == 2
    assert 'Mock answer' in output['answer']
    assert (artifact_dir / 'answer-run' / 'answer.json').exists()
    assert (artifact_dir / 'answer-run' / 'report.md').exists()
    assert (artifact_dir / 'answer-run' / 'summary.json').exists()
    answer_payload = json.loads((artifact_dir / 'answer-run' / 'answer.json').read_text(encoding='utf-8'))
    assert answer_payload['citation_count'] == 2
    assert answer_payload['citations'][0]['title'] == 'Florida appraisal clause overview'


def test_research_command_smoke_emits_json_and_artifact(tmp_path, capsys) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
    artifact_dir = tmp_path / 'artifacts'

    exit_code = main(
        [
            'research',
            'Summarize the Florida CAT market outlook.',
            '--mode',
            'smoke',
            '--run-id',
            'research-run',
            '--sqlite-path',
            str(sqlite_path),
            '--artifact-dir',
            str(artifact_dir),
            '--json',
        ]
    )

    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output['workflow'] == 'research'
    assert output['run_id'] == 'research-run'
    assert output['citation_count'] == 5
    assert 'Search-backed research report' in output['report']
    assert (artifact_dir / 'research-run' / 'research.json').exists()
    assert (artifact_dir / 'research-run' / 'research.md').exists()
    assert (artifact_dir / 'research-run' / 'report.md').exists()
    assert (artifact_dir / 'research-run' / 'summary.json').exists()
    research_payload = json.loads((artifact_dir / 'research-run' / 'research.json').read_text(encoding='utf-8'))
    assert research_payload['citation_count'] == 5
    assert research_payload['citations'][0]['title'] == 'Mock Research Source 1'
    assert research_payload['grounding_count'] == 5
    assert research_payload['grounding'][0]['title'] == 'Mock Research Source 1'
    assert research_payload['grounding'][0]['snippet'].startswith('Grounding basis - ')
    assert research_payload['grounding'][0]['snippet'] != research_payload['citations'][0]['snippet']
    assert research_payload['output_content'].startswith('Search-backed research report.')
    assert research_payload['request_payload']['type'] == 'deep-reasoning'
    assert research_payload['request_payload']['contents']['highlights'] == {'maxCharacters': 2666}
    assert_no_deprecated_request_fields(research_payload['request_payload'])
    research_markdown = (artifact_dir / 'research-run' / 'research.md').read_text(encoding='utf-8')
    assert '# Research Report' in research_markdown
    assert '## Grounding / Source Review' in research_markdown
    summary_payload = json.loads((artifact_dir / 'research-run' / 'summary.json').read_text(encoding='utf-8'))
    assert summary_payload['extra']['runtime']['execution_mode'] == 'smoke'


def test_research_command_live_requires_api_key(tmp_path, monkeypatch) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
    artifact_dir = tmp_path / 'artifacts'

    from exa_demo import cli as cli_module

    monkeypatch.setattr(cli_module, 'load_dotenv', lambda: None)
    monkeypatch.delenv('EXA_API_KEY', raising=False)

    with pytest.raises(RuntimeError, match='Missing EXA_API_KEY'):
        main(
            [
                'research',
                'Summarize the Florida CAT market outlook.',
                '--mode',
                'live',
                '--sqlite-path',
                str(sqlite_path),
                '--artifact-dir',
                str(artifact_dir),
            ]
        )


def test_structured_search_command_smoke_emits_json_and_artifact(tmp_path, capsys) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
    artifact_dir = tmp_path / 'artifacts'
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

    exit_code = main(
        [
            'structured-search',
            'independent adjuster florida catastrophe claims',
            '--schema-file',
            str(schema_file),
            '--mode',
            'smoke',
            '--run-id',
            'structured-run',
            '--sqlite-path',
            str(sqlite_path),
            '--artifact-dir',
            str(artifact_dir),
            '--json',
        ]
    )

    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output['workflow'] == 'structured-search'
    assert output['run_id'] == 'structured-run'
    assert output['schema_file'] == str(schema_file)
    assert output['structured_output']['name'].startswith('Mock name for query:')
    assert output['structured_output']['role'].startswith('Mock role for query:')
    assert (artifact_dir / 'structured-run' / 'structured_output.json').exists()
    assert (artifact_dir / 'structured-run' / 'report.md').exists()
    assert (artifact_dir / 'structured-run' / 'summary.json').exists()
    structured_payload = json.loads((artifact_dir / 'structured-run' / 'structured_output.json').read_text(encoding='utf-8'))
    assert structured_payload['structured_output'] == structured_payload['output_content']
    assert structured_payload['structured_output_keys'] == ['name', 'role']
    assert structured_payload['grounding_count'] == 5
    assert structured_payload['grounding'][0]['url'].startswith('https://www.linkedin.com/')
    assert structured_payload['grounding'][0]['snippet'].startswith('Grounding basis - ')
    assert 'grounding' not in structured_payload['output_content']
    assert 'citations' not in structured_payload['output_content']
    assert structured_payload['request_payload']['contents']['highlights'] == {'maxCharacters': 2666}
    assert_no_deprecated_request_fields(structured_payload['request_payload'])


def test_structured_search_command_live_requires_api_key(tmp_path, monkeypatch) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
    artifact_dir = tmp_path / 'artifacts'
    schema_file = tmp_path / 'structured-schema.json'
    schema_file.write_text(json.dumps({'type': 'object', 'properties': {'name': {'type': 'string'}}}), encoding='utf-8')

    from exa_demo import cli as cli_module

    monkeypatch.setattr(cli_module, 'load_dotenv', lambda: None)
    monkeypatch.delenv('EXA_API_KEY', raising=False)

    with pytest.raises(RuntimeError, match='Missing EXA_API_KEY'):
        main(
            [
                'structured-search',
                'independent adjuster florida catastrophe claims',
                '--schema-file',
                str(schema_file),
                '--mode',
                'live',
                '--sqlite-path',
                str(sqlite_path),
                '--artifact-dir',
                str(artifact_dir),
            ]
        )


def test_find_similar_command_smoke_emits_json_and_artifact(tmp_path, capsys) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
    artifact_dir = tmp_path / 'artifacts'

    exit_code = main(
        [
            'find-similar',
            'https://www.merlinlawgroup.com/',
            '--mode',
            'smoke',
            '--run-id',
            'find-similar-run',
            '--sqlite-path',
            str(sqlite_path),
            '--artifact-dir',
            str(artifact_dir),
            '--json',
        ]
    )

    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output['workflow'] == 'find-similar'
    assert output['run_id'] == 'find-similar-run'
    assert output['seed_url'] == 'https://www.merlinlawgroup.com/'
    assert output['result_count'] == 3
    assert output['top_result']['title'] == 'Florida Insurance Litigation Firm'
    assert (artifact_dir / 'find-similar-run' / 'find_similar.json').exists()
    assert (artifact_dir / 'find-similar-run' / 'report.md').exists()
    assert (artifact_dir / 'find-similar-run' / 'summary.json').exists()
    artifact_payload = json.loads((artifact_dir / 'find-similar-run' / 'find_similar.json').read_text(encoding='utf-8'))
    assert artifact_payload['seed_url'] == 'https://www.merlinlawgroup.com/'
    assert artifact_payload['result_count'] == 3
    assert artifact_payload['top_result']['title'] == 'Florida Insurance Litigation Firm'
    assert_no_deprecated_request_fields(artifact_payload['request_payload'])


def test_find_similar_command_live_requires_api_key(tmp_path, monkeypatch) -> None:
    sqlite_path = tmp_path / 'cache.sqlite'
    artifact_dir = tmp_path / 'artifacts'

    from exa_demo import cli as cli_module

    monkeypatch.setattr(cli_module, 'load_dotenv', lambda: None)
    monkeypatch.delenv('EXA_API_KEY', raising=False)

    with pytest.raises(RuntimeError, match='Missing EXA_API_KEY'):
        main(
            [
                'find-similar',
                'https://www.merlinlawgroup.com/',
                '--mode',
                'live',
                '--sqlite-path',
                str(sqlite_path),
                '--artifact-dir',
                str(artifact_dir),
            ]
        )
