from __future__ import annotations

from pathlib import Path

from exa_demo.client_payloads import (
    build_exa_payload,
    build_find_similar_payload,
    build_research_payload,
)
from exa_demo.config import default_config
from exa_demo.workflows import (
    build_answer_artifact,
    build_find_similar_artifact,
    build_research_artifact,
    build_structured_search_artifact,
)


def test_build_exa_payload_trims_additional_queries_and_dates() -> None:
    config = default_config()
    config.update(
        {
            'additional_queries': [' licensed public adjuster Florida ', '', '  '],
            'start_published_date': ' 2026-01-01 ',
            'end_published_date': ' ',
        }
    )

    payload = build_exa_payload('insurance expert witness', config)

    assert payload['additionalQueries'] == ['licensed public adjuster Florida']
    assert payload['startPublishedDate'] == '2026-01-01'
    assert 'endPublishedDate' not in payload
    assert payload['contents']['highlights'] == {'maxCharacters': 2666}
    assert 'livecrawl' not in payload
    assert 'highlightsPerUrl' not in payload['contents']['highlights']
    assert 'numSentences' not in payload['contents']['highlights']


def test_build_find_similar_payload_ignores_deprecated_crawl_dates() -> None:
    payload = build_find_similar_payload(
        'https://example.com/article',
        default_config(),
        start_crawl_date=' 2026-01-01 ',
        end_crawl_date='',
        start_published_date=' 2026-01-15 ',
        end_published_date='   ',
    )

    assert 'startCrawlDate' not in payload
    assert 'endCrawlDate' not in payload
    assert payload['startPublishedDate'] == '2026-01-15'
    assert 'endPublishedDate' not in payload
    assert payload['contents']['text'] is True


def test_build_research_payload_uses_modern_search_controls() -> None:
    config = default_config()
    config['max_age_hours'] = 1

    payload = build_research_payload('Summarize the Florida CAT market outlook.', config)

    assert payload['type'] == 'deep-reasoning'
    assert payload['contents']['highlights'] == {'maxCharacters': 2666}
    assert payload['contents']['maxAgeHours'] == 1
    assert 'livecrawl' not in payload
    assert 'highlightsPerUrl' not in payload['contents']['highlights']
    assert 'numSentences' not in payload['contents']['highlights']


def test_build_answer_artifact_normalizes_base_fields() -> None:
    payload = build_answer_artifact(
        'What is the Florida appraisal clause dispute process?',
        request_payload={'query': 'What is the Florida appraisal clause dispute process?'},
        response_json={'requestId': ' req-answer ', 'answer': 'Mock answer', 'costDollars': {'total': '0.01'}},
        cache_hit=True,
        estimated_cost_usd=0.02,
    )

    assert payload['request_id'] == 'req-answer'
    assert payload['cache_hit'] is True
    assert payload['estimated_cost_usd'] == 0.02
    assert payload['actual_cost_usd'] == 0.01
    assert payload['answer_text'] == 'Mock answer'


def test_build_research_artifact_prefers_sources_when_citations_missing() -> None:
    payload = build_research_artifact(
        'Summarize the Florida CAT market outlook.',
        request_payload={'query': 'Summarize the Florida CAT market outlook.'},
        response_json={
            'requestId': 'req-research',
            'report': 'Mock report',
            'sources': [
                {
                    'name': 'Florida Market Bulletin',
                    'sourceUrl': 'https://example.com/bulletin',
                    'text': 'Market bulletin summary',
                }
            ],
            'costDollars': {'total': 0.0},
        },
        cache_hit=False,
        estimated_cost_usd=0.01,
    )

    assert payload['request_id'] == 'req-research'
    assert payload['citation_count'] == 1
    assert payload['citations'][0]['title'] == 'Florida Market Bulletin'
    assert payload['report_preview'] == 'Mock report'


def test_build_research_artifact_synthesizes_report_from_search_results() -> None:
    payload = build_research_artifact(
        'Summarize the Florida CAT market outlook.',
        request_payload={
            'query': 'Summarize the Florida CAT market outlook.',
            'type': 'deep-reasoning',
        },
        response_json={
            'requestId': 'req-research-search',
            'searchType': 'deep-reasoning',
            'results': [
                {
                    'title': 'Florida Market Bulletin',
                    'url': 'https://example.com/bulletin',
                    'snippet': 'Market conditions remain dynamic.',
                }
            ],
            'costDollars': {'total': 0.0},
        },
        cache_hit=False,
        estimated_cost_usd=0.01,
    )

    assert payload['request_id'] == 'req-research-search'
    assert payload['citation_count'] == 1
    assert payload['citations'][0]['title'] == 'Florida Market Bulletin'
    assert payload['report_text'].startswith('Search-backed research report.')
    assert 'Market conditions remain dynamic.' in payload['report_text']


def test_build_research_artifact_reads_modern_output_content() -> None:
    payload = build_research_artifact(
        'Summarize the Florida CAT market outlook.',
        request_payload={
            'query': 'Summarize the Florida CAT market outlook.',
            'type': 'deep-reasoning',
        },
        response_json={
            'requestId': 'req-research-output',
            'searchType': 'deep-reasoning',
            'output': {
                'content': 'Modern research report from output content.',
                'grounding': [
                    {
                        'title': 'Florida Market Bulletin',
                        'url': 'https://example.com/bulletin',
                    }
                ],
            },
            'results': [
                {
                    'title': 'Florida Market Bulletin',
                    'url': 'https://example.com/bulletin',
                    'snippet': 'Market conditions remain dynamic.',
                }
            ],
            'costDollars': {'total': 0.0},
        },
        cache_hit=False,
        estimated_cost_usd=0.01,
    )

    assert payload['request_id'] == 'req-research-output'
    assert payload['report_text'] == 'Modern research report from output content.'
    assert payload['citation_count'] == 1
    assert payload['response']['output']['grounding'][0]['title'] == 'Florida Market Bulletin'


def test_build_find_similar_artifact_sets_top_result_and_score() -> None:
    payload = build_find_similar_artifact(
        'https://example.com/article',
        request_payload={'url': 'https://example.com/article'},
        response_json={
            'requestId': 'req-find-similar',
            'results': [
                {
                    'title': 'Florida Insurance Litigation Firm',
                    'url': 'https://example.com/firm',
                    'snippet': 'Mock result',
                    'score': '0.98',
                }
            ],
            'costDollars': {'total': 0.0},
        },
        cache_hit=False,
        estimated_cost_usd=0.01,
    )

    assert payload['request_id'] == 'req-find-similar'
    assert payload['result_count'] == 1
    assert payload['top_result']['title'] == 'Florida Insurance Litigation Firm'
    assert payload['results'][0]['score'] == 0.98


def test_build_structured_search_artifact_sorts_structured_keys(tmp_path: Path) -> None:
    schema_file = tmp_path / 'schema.json'
    schema_file.write_text('{"type":"object"}\n', encoding='utf-8')

    payload = build_structured_search_artifact(
        'insurance expert witness',
        schema_path=schema_file,
        request_payload={'query': 'insurance expert witness'},
        response_json={
            'requestId': 'req-structured',
            'structuredOutput': {
                'records': [{'name': 'Jane Doe'}],
                'schema_title': 'Structured Professionals',
                'field_names': ['name'],
            },
            'costDollars': {'total': 0.0},
        },
        cache_hit=False,
        estimated_cost_usd=0.01,
    )

    assert payload['request_id'] == 'req-structured'
    assert payload['schema_file'] == str(schema_file)
    assert payload['structured_output_keys'] == ['field_names', 'records', 'schema_title']


def test_build_structured_search_artifact_reads_modern_output_content(tmp_path: Path) -> None:
    schema_file = tmp_path / 'schema.json'
    schema_file.write_text('{"type":"object"}\n', encoding='utf-8')

    payload = build_structured_search_artifact(
        'insurance expert witness',
        schema_path=schema_file,
        request_payload={'query': 'insurance expert witness'},
        response_json={
            'requestId': 'req-structured-output',
            'searchType': 'auto',
            'output': {
                'content': {
                    'records': [{'name': 'Jane Doe'}],
                    'schema_title': 'Structured Professionals',
                },
                'grounding': [
                    {
                        'title': 'Jane Doe',
                        'url': 'https://example.com/profile',
                    }
                ],
            },
            'costDollars': {'total': 0.0},
        },
        cache_hit=False,
        estimated_cost_usd=0.01,
    )

    assert payload['request_id'] == 'req-structured-output'
    assert payload['structured_output']['records'][0]['name'] == 'Jane Doe'
    assert payload['structured_output_keys'] == ['records', 'schema_title']
    assert payload['response']['output']['grounding'][0]['url'] == 'https://example.com/profile'
