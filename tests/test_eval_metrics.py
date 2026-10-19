"""Hand-computed metric examples and mock-only evaluator control-flow checks."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from eval.metrics import extract_numbers, numbers_are_grounded, selection_scores, wilson
from eval.run_agent_eval import load_questions, render_report, run_questions


def test_accuracy_precision_and_recall_examples():
    rows = [selection_scores(['a', 'b'], ['a']), selection_scores(['a'], ['a', 'c'])]
    assert sum(row['exact'] for row in rows) == 0
    assert sum(row['precision'] for row in rows) / 2 == 0.75
    assert sum(row['recall'] for row in rows) / 2 == 0.75
    assert selection_scores(['a', 'b'], ['b', 'a'])['exact'] == 1
    assert selection_scores([], []) == dict(exact=1, precision=1, recall=1)
    assert selection_scores([], ['a']) == dict(exact=0, precision=0, recall=0)
    assert selection_scores(['a'], []) == dict(exact=0, precision=0, recall=0)


def test_wilson_hand_computed_bounds():
    assert wilson(5, 10) == pytest.approx((0.2365930905, 0.7634069095))
    assert wilson(0, 10) == pytest.approx((0, 0.2775327999))
    assert wilson(20, 20) == pytest.approx((0.8388748419, 1))
    assert wilson(0, 0) is None
    with pytest.raises(ValueError):
        wilson(11, 10)


def test_number_extractor_formats_signs_and_rounding():
    numbers = extract_numbers('Revenue $1,234.50, down -12.5%; loss -$250 and $-75; total $1.2K in 2026.')
    assert [(n.value, n.kind) for n in numbers] == [
        (1234.5, 'dollar'), (-12.5, 'percent'), (-250, 'dollar'),
        (-75, 'dollar'), (1200, 'dollar'), (2026, 'number'),
    ]
    assert numbers[0].tolerance == pytest.approx(0.005)
    assert numbers[4].tolerance == pytest.approx(50)


def test_faithfulness_heuristic_rejects_unsupported_figures():
    raw = {'revenue': 1234.5}
    computed = {'share': 12.54}
    assert numbers_are_grounded('Revenue $1,235; share 12.5%.', raw, computed) is True
    assert numbers_are_grounded('Revenue $9,999; share 12.5%.', raw, computed) is False
    assert numbers_are_grounded('Revenue $1.2K.', raw, {}) is True
    assert numbers_are_grounded('The latest month was strong.', raw, computed) is None


def test_question_sheet_and_offline_runner_never_call_model():
    from api import main
    questions = load_questions(Path(__file__).resolve().parents[1] / 'eval/questions.yaml')
    fake_api = Mock()
    fake_api.keyword_fallback.side_effect = main.keyword_fallback
    rows, observations, stopped = run_questions(fake_api, questions)
    assert len(rows) == 30 and observations == [] and stopped is None
    fake_api.planner_node.assert_not_called()
    fake_api.get_model.assert_not_called()
    report = render_report(questions, rows, observations, 'offline', None, False)
    assert '53.3%' in report and 'n=30' in report
    assert 'pending first live run' in report
    assert 'Model: none (keyword_fallback only)' in report.splitlines()[:8]
    assert '| top_products | 4 of 5 | 5 |' in report
    assert '| out_of_scope | 0 of 5 | 5 |' in report
    for label in ('exact-match tool selection', 'mean precision', 'mean recall'):
        assert f'| keyword_fallback baseline (not the LLM): {label} |' in report


def test_mock_planner_observes_pre_fallback_empty_and_cap():
    from api import main
    question = dict(id='Q01', question='test', category='out_of_scope', expected_tools=[])
    client = Mock()
    client.generate_content.return_value.text = ','.join(main.TOOLS)
    rows, observations, stopped = run_questions(main, [question], client=client)
    assert rows[0]['got'] == list(main.TOOLS)[:3]
    assert observations[0]['raw_tools'] == list(main.TOOLS)
    assert observations[0]['cap_applied'] is True
    client.generate_content.return_value.text = 'invented_tool'
    rows, observations, stopped = run_questions(main, [question], client=client)
    assert observations[0]['raw_tools'] == []
    assert observations[0]['monthly_fallback'] is True
    assert rows[0]['got'] == ['monthly_revenue']
    report = render_report([question], rows, observations, 'live', None, False,
                           model_name='configured-test-model')
    assert 'Model: configured-test-model' in report.splitlines()[:8]
    assert '| Questions with cap applied (count) | 0 of 1 |' in report
    for label in ('Exact-match tool-selection accuracy', 'Mean per-question precision', 'Mean per-question recall'):
        assert f'| {label} |' in report
    assert 'keyword_fallback baseline (not the LLM)' not in report


def test_mock_quota_stop_and_sleep_between_calls():
    from api import main
    from google.api_core.exceptions import ResourceExhausted
    question = dict(id='Q01', question='test', category='monthly_revenue', expected_tools=['monthly_revenue'])
    client = Mock()
    client.generate_content.side_effect = [Mock(text='monthly_revenue'), ResourceExhausted('synthetic quota')]
    sleep = Mock()
    rows, observations, stopped = run_questions(main, [question, dict(question, id='Q02'),
        dict(question, id='Q03')], client=client, delay=2, sleep=sleep)
    assert len(rows) == 1 and len(observations) == 2
    assert observations[-1]['outcome'] == 'quota'
    assert stopped.startswith('ResourceExhausted:')
    assert client.generate_content.call_count == 2
    sleep.assert_called_once_with(2)


def test_mock_analyst_quota_is_not_mistaken_for_completed_answer(monkeypatch):
    from api import main
    from google.api_core.exceptions import ResourceExhausted
    question = dict(id='Q01', question='test', category='monthly_revenue', expected_tools=['monthly_revenue'])
    client = Mock()
    client.generate_content.side_effect = [Mock(text='monthly_revenue'), ResourceExhausted('synthetic quota')]
    # No database calls: only exercise the existing analyst's quota-catching path.
    monkeypatch.setattr(main, 'tool_node', lambda state: state)
    monkeypatch.setattr(main, 'compute_node', lambda state: state)
    rows, observations, stopped = run_questions(main, [question], client=client, with_answers=True)
    assert rows == [] and len(observations) == 1
    assert observations[0]['outcome'] == 'quota'
    assert stopped.startswith('ResourceExhausted:')


@pytest.mark.parametrize('answer,faithful', [
    ('Revenue $1,000 and share 25%.', True),
    ('Revenue $9,999 and share 25%.', False),
])
def test_mock_answer_numerical_check(monkeypatch, answer, faithful):
    from api import main
    question = dict(id='Q01', question='test', category='monthly_revenue', expected_tools=['monthly_revenue'])
    client = Mock()
    client.generate_content.side_effect = [Mock(text='monthly_revenue'), Mock(text=answer)]

    def tools(state):
        state.raw_data = {'revenue': 1000}
        state.computed_data = {'share': 25}
        return state

    monkeypatch.setattr(main, 'tool_node', tools)
    monkeypatch.setattr(main, 'compute_node', lambda state: state)
    rows, observations, stopped = run_questions(main, [question], client=client, with_answers=True)
    assert stopped is None and rows[0]['faithful'] is faithful
    assert client.generate_content.call_count == 2
