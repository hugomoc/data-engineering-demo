"""Live-path control flow with fake model responses and temporary progress only."""

from contextlib import redirect_stdout
from enum import Enum
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from google.api_core.exceptions import (
    InvalidArgument, NotFound, PermissionDenied, ResourceExhausted, Unauthenticated,
)

from api import main as api
from eval.run_agent_eval import ModelProbe, load_questions, render_report, run_questions


class FakeModel:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = 0

    def generate_content(self, *args, **kwargs):
        self.calls += 1
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return SimpleNamespace(text=response) if isinstance(response, str) else response


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
    assert '| Q02 | top_products | call failed | call failed | none | CALL FAILED |' in text


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
    assert observations[0]['raw_status'] == 'declined'
    assert '| Out-of-scope: model declined | 1 of 1 |' in text
    assert 'n=1)' in text


def test_resume_skips_completed_and_reruns_failed(tmp_path, capsys):
    progress = tmp_path / 'progress.jsonl'
    sheet = questions()[:3]
    first = FakeModel(','.join(api.TOOLS), ResourceExhausted('quota'))
    result = run(first, sheet, progress_path=progress)
    assert len(result[0]) == 1
    entries = [json.loads(line) for line in progress.read_text().splitlines()]
    assert [entry['outcome'] for entry in entries] == ['ok', 'quota']
    assert all(set(entry) == {'id', 'outcome', 'tools', 'raw_status', 'valid_tool_count'} for entry in entries)
    assert entries[0]['raw_status'] == 'picked' and entries[0]['valid_tool_count'] == 4
    assert entries[1]['raw_status'] is None  # No response was observed on a failed API call.
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
    progress.write_text(json.dumps(dict(id='Q02', outcome='ok', tools=['top_products'], raw_status='picked', valid_tool_count=1)) + '\n')
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
    assert json.loads(progress.read_text()) == dict(id='Q01', outcome='auth', tools=[], raw_status=None, valid_tool_count=None)


def test_invalid_argument_without_key_is_retried():
    model = FakeModel(InvalidArgument('temporary invalid input'), 'top_products')
    rows, observations, stopped = run(model, questions()[:1])
    assert len(rows) == 1 and model.calls == 2 and stopped is None
    assert observations[0]['outcome'] == 'other'


class BlockReason(Enum):
    SAFETY = 'private-block-value'


class FinishReason(Enum):
    STOP = 'private-finish-value'


class FakeResponse:
    def __init__(self, text='top_products', *, unreadable=False, metadata=True):
        self._text = text
        self.unreadable = unreadable
        if metadata:
            self.prompt_feedback = SimpleNamespace(block_reason=BlockReason.SAFETY)
            self.candidates = [SimpleNamespace(finish_reason=FinishReason.STOP)]

    @property
    def text(self):
        if self.unreadable:
            raise ValueError('private-response-body-and-exception-message')
        return self._text


def test_text_failure_is_no_text_without_failed_call(tmp_path):
    sheet = [questions()[-1]]
    progress = tmp_path / 'progress.jsonl'
    result = run(FakeModel(FakeResponse(unreadable=True)), sheet, progress_path=progress)
    rows, observations, stopped = result
    assert stopped is None and len(rows) == 1
    assert observations[0]['raw_status'] == 'no_text'
    assert observations[0]['raw_tools'] is None
    assert observations[0]['valid_tool_count'] is None
    assert observations[0]['text_error'] == 'ValueError'
    text = report(sheet, result)
    for label in ('Out-of-scope: no usable response', 'Questions with no usable model text',
                  'Final tools came from keyword fallback after no usable response'):
        assert f'| {label} | 1 of 1 |' in text
    assert '| Failed calls (count) | 0 |' in text
    assert '| Out-of-scope: model declined | 0 of 1 |' in text
    assert '| no text | monthly_revenue |' in text
    entry = json.loads(progress.read_text())
    assert entry['raw_status'] == 'no_text' and entry['tools'] is None
    assert entry['text_error'] == 'ValueError'
    assert 'private-response-body-and-exception-message' not in text + progress.read_text()


def test_empty_parse_is_declined_with_keyword_fallback(tmp_path):
    sheet = [dict(questions()[-1], question='Which customer segment has the best lifetime value?')]
    progress = tmp_path / 'progress.jsonl'
    result = run(FakeModel('invented-private-response-body'), sheet, progress_path=progress)
    rows, observations, _ = result
    assert rows[0]['got'] == ['revenue_by_segment']
    assert observations[0]['raw_status'] == 'declined' and observations[0]['raw_tools'] == []
    assert observations[0]['valid_tool_count'] == 0
    text = report(sheet, result)
    assert '| Final tools came from keyword fallback after the model declined | 1 of 1 |' in text
    assert '| Final tools came from keyword fallback after no usable response | 0 of 1 |' in text
    assert '| [] | revenue_by_segment |' in text
    assert json.loads(progress.read_text())['raw_status'] == 'declined'
    assert 'invented-private-response-body' not in text + progress.read_text()


def test_normal_reply_is_picked_with_pre_cap_count_and_only_safe_names(tmp_path):
    sheet = [questions()[-1]]
    progress = tmp_path / 'progress.jsonl'
    payload = ','.join(api.TOOLS) + ', private-model-response-body'
    result = run(FakeModel(FakeResponse(payload)), sheet, progress_path=progress)
    rows, observations, _ = result
    assert observations[0]['raw_status'] == 'picked'
    assert observations[0]['valid_tool_count'] == 4 and observations[0]['cap_applied'] is True
    assert rows[0]['got'] == list(api.TOOLS)[:3]
    entry = json.loads(progress.read_text())
    assert entry['tools'] == list(api.TOOLS) and entry['valid_tool_count'] == 4
    assert entry['block_reason'] == 'SAFETY' and entry['finish_reason'] == 'STOP'
    text = report(sheet, result)
    assert 'block_reason=SAFETY' in text and 'finish_reason=STOP' in text
    assert 'Model raw | Got (final)' in text
    assert '(final tools after app fallback and cap)' in text
    assert '| Out-of-scope: model picked tools | 1 of 1 |' in text
    for private in ('private-block-value', 'private-finish-value', 'private-model-response-body', payload):
        assert private not in text + progress.read_text()


@pytest.mark.parametrize('response', [
    FakeResponse('top_products,monthly_revenue,revenue_by_segment,anomalies_sales'),
    FakeResponse('no-valid-tool'), FakeResponse(unreadable=True),
])
def test_probe_preserves_planner_behavior(response):
    question = 'Which segment?'
    with patch.object(api, 'get_model', return_value=FakeModel(response)), redirect_stdout(io.StringIO()):
        expected = api.planner_node(api.AgentState(question)).selected_tools
    probe = ModelProbe(FakeModel(response))
    with patch.object(api, 'get_model', return_value=probe), redirect_stdout(io.StringIO()):
        actual = api.planner_node(api.AgentState(question)).selected_tools
    assert actual == expected
    assert probe.error is None
    if response.unreadable:
        assert probe.responses[0]['text_error'] == 'ValueError'
    assert not any('private-' in str(value) for value in probe.responses[0].values())


def test_missing_or_non_enum_metadata_is_not_stringified(tmp_path):
    response = FakeResponse(metadata=False)
    response.prompt_feedback = SimpleNamespace(block_reason='private-string-value')
    response.candidates = [SimpleNamespace(finish_reason=123)]
    progress = tmp_path / 'progress.jsonl'
    result = run(FakeModel(response), questions()[:1], progress_path=progress)
    entry = json.loads(progress.read_text())
    assert 'block_reason' not in entry and 'finish_reason' not in entry
    assert 'private-string-value' not in report(questions()[:1], result) + progress.read_text()


def test_resume_preserves_no_text_distinction_and_exception_fallback(tmp_path):
    sheet = [dict(questions()[-1], question='Which segment?')]
    progress = tmp_path / 'progress.jsonl'
    run(FakeModel(FakeResponse(unreadable=True)), sheet, progress_path=progress)
    no_calls = FakeModel()
    result = run(no_calls, sheet, progress_path=progress, resume=True)
    assert no_calls.calls == 0
    assert result[0][0]['got'] == ['monthly_revenue']  # App exception fallback, not segment keyword routing.
    assert result[0][0]['raw_status'] == 'no_text' and result[0][0]['raw_tools'] is None
    assert '| Questions with no usable model text | 1 of 1 |' in report(sheet, result)


def test_legacy_progress_is_rejected_without_guessing_empty_observations(tmp_path):
    progress = tmp_path / 'progress.jsonl'
    progress.write_text(json.dumps(dict(id='Q01', outcome='ok', tools=[])) + '\n')
    client = FakeModel()
    with pytest.raises(ValueError, match='archive the old file'):
        run(client, questions()[:1], progress_path=progress, resume=True)
    assert client.calls == 0
