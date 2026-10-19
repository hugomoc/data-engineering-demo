"""Live-path control flow with fake model responses and temporary progress only."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.api_core.exceptions import (
    InvalidArgument, NotFound, PermissionDenied, ResourceExhausted, Unauthenticated,
)

from api import main as api
from eval.run_agent_eval import load_questions, render_report, run_questions


class FakeModel:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = 0

    def generate_content(self, *args, **kwargs):
        self.calls += 1
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return SimpleNamespace(text=response)


def questions():
    return load_questions(Path(__file__).resolve().parents[1] / 'eval/questions.yaml')


def run(model, sheet=None, **kwargs):
    return run_questions(api, questions() if sheet is None else sheet,
                         client=model, sleep=lambda _: None, **kwargs)


def report(sheet, result):
    return render_report(sheet, *result[:2], 'live', result[2], False, model_name='fake-model')


@pytest.mark.parametrize('error,outcome', [
    (ResourceExhausted('quota'), 'quota'),
    (PermissionDenied('denied'), 'auth'),
    (Unauthenticated('credentials'), 'auth'),
    (InvalidArgument('API key not valid'), 'auth'),
    (NotFound('model unavailable'), 'model_error'),
])
def test_terminal_errors_stop_and_exclude_every_denominator(error, outcome):
    sheet = questions()
    model = FakeModel('top_products', error)
    result = run(model, sheet)
    rows, observations, stopped = result
    assert len(rows) == 1 and model.calls == 2
    assert observations[-1]['outcome'] == outcome
    assert type(error).__name__ in stopped
    text = report(sheet, result)
    assert 'PARTIAL: 1 of 30 questions evaluated' in text
    assert '| Failed calls (count) | 1 |' in text
    assert '| Questions not run (count) | 28 |' in text
    assert '| Questions with cap applied (count) | 0 of 1 |' in text
    assert '| top_products | 1 of 1 | 1 |' in text
    assert '100.0% (95% Wilson' in text and 'n=1)' in text
    assert '| Q02 | top_products | call failed | CALL FAILED |' in text


def test_http_429_also_stops():
    error = RuntimeError('HTTP quota')
    error.response = SimpleNamespace(status_code=429)
    model = FakeModel(error)
    rows, observations, stopped = run(model)
    assert rows == [] and observations[0]['outcome'] == 'quota'
    assert model.calls == 1 and stopped


def test_transient_failure_retried_once_then_excluded():
    model = FakeModel(RuntimeError('temporary'), RuntimeError('still down'), 'top_products')
    sheet = questions()[:2]
    result = run(model, sheet)
    rows, observations, stopped = result
    assert model.calls == 3 and stopped is None
    assert [row['id'] for row in rows] == ['Q02']
    text = report(sheet, result)
    assert '| Failed calls (count) | 2 |' in text
    assert '| Questions not run (count) | 0 |' in text
    assert '| top_products | 1 of 1 | 1 |' in text


def test_recovered_transient_failure_counts_only_reply():
    model = FakeModel(RuntimeError('temporary'), 'top_products')
    sheet = questions()[:1]
    result = run(model, sheet)
    assert model.calls == 2 and len(result[0]) == 1
    assert '| Failed calls (count) | 1 |' in report(sheet, result)
    assert '| Questions with cap applied (count) | 0 of 1 |' in report(sheet, result)


def test_garbage_is_replied_with_no_valid_tool_and_preserves_app_fallback():
    sheet = [questions()[-1]]
    result = run(FakeModel('invented_tool'), sheet)
    rows, observations, stopped = result
    assert len(rows) == 1 and stopped is None
    assert observations[0]['outcome'] == 'ok' and observations[0]['raw_tools'] == []
    # The evaluator still measures app routing, separately showing the raw empty reply.
    assert rows[0]['got'] == api.keyword_fallback(sheet[0]['question'])
    text = report(sheet, result)
    assert '| Failed calls (count) | 0 |' in text
    assert '| Model selected no valid tool on out-of-scope input, before fallback | 100.0%' in text
    assert 'n=1)' in text


def test_resume_skips_completed_and_reruns_failed(tmp_path, capsys):
    progress = tmp_path / 'progress.jsonl'
    sheet = questions()[:3]
    first = FakeModel(','.join(api.TOOLS), ResourceExhausted('quota'))
    result = run(first, sheet, progress_path=progress)
    assert len(result[0]) == 1
    entries = [json.loads(line) for line in progress.read_text().splitlines()]
    assert [entry['outcome'] for entry in entries] == ['ok', 'quota']
    assert all(set(entry) == {'id', 'outcome', 'tools'} for entry in entries)
    assert entries[0]['tools'] == list(api.TOOLS)
    second = FakeModel('top_products', 'top_products')
    result = run(second, sheet, progress_path=progress, resume=True)
    assert second.calls == 2 and len(result[0]) == 3 and result[2] is None
    assert 'skipped 1 completed questions' in capsys.readouterr().out
    assert '| Questions with cap applied (count) | 1 of 3 |' in report(sheet, result)
    third = FakeModel()
    assert len(run(third, sheet, progress_path=progress, resume=True)[0]) == 3
    assert third.calls == 0


def test_resume_retains_later_completed_ids_when_retry_stops(tmp_path):
    progress = tmp_path / 'progress.jsonl'
    sheet = questions()[:2]
    progress.write_text(json.dumps(dict(id='Q02', outcome='ok', tools=['top_products'])) + '\n')
    result = run(FakeModel(NotFound('gone')), sheet, progress_path=progress, resume=True)
    assert [row['id'] for row in result[0]] == ['Q02']
    assert '| Questions not run (count) | 0 |' in report(sheet, result)


def test_zero_replies_partial_without_headline_accuracy(capsys):
    sheet = questions()
    result = run(FakeModel(ResourceExhausted('quota')), sheet)
    text = report(sheet, result)
    assert '**PARTIAL: 0 of 30 questions evaluated**' in text.splitlines()[:8]
    assert 'Model: fake-model' in text.splitlines()[:8]
    assert 'no valid planner responses' in text
    assert 'Exact-match tool-selection accuracy' not in text
    assert 'Mean per-question precision' not in text
    assert 'Mean per-question recall' not in text
    assert 'n=0)' in text and 'n=1)' not in text
    print(text)
    assert 'PARTIAL: 0 of 30 questions evaluated' in capsys.readouterr().out


def test_masked_error_has_no_key_in_output_report_or_progress(monkeypatch, tmp_path, capsys):
    key = 'synthetic-private-key-for-test'
    monkeypatch.setenv('GEMINI_API_KEY', key)
    progress = tmp_path / 'progress.jsonl'
    result = run(FakeModel(InvalidArgument(f'API key not valid: {key}')), progress_path=progress)
    text = capsys.readouterr().out + report(questions(), result) + progress.read_text()
    assert key not in text and '[REDACTED]' in text
    assert 'InvalidArgument' in text
    assert json.loads(progress.read_text()) == dict(id='Q01', outcome='auth', tools=[])


def test_invalid_argument_without_key_is_retried():
    model = FakeModel(InvalidArgument('temporary invalid input'), 'top_products')
    rows, observations, stopped = run(model, questions()[:1])
    assert len(rows) == 1 and model.calls == 2 and stopped is None
    assert observations[0]['outcome'] == 'other'
