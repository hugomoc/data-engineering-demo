"""Evaluate draft question labels on a disposable fixture; offline by default."""

import argparse
from collections import Counter
from contextlib import redirect_stdout
import json
import os
import re
from pathlib import Path
import runpy
import tempfile
import time
from unittest.mock import patch

import yaml

from eval.fixture import ROOT, build_database
from eval.metrics import numbers_are_grounded, selection_scores, wilson


CATEGORIES = ('top_products', 'revenue_by_segment', 'monthly_revenue',
              'anomalies_sales', 'multi_tool', 'out_of_scope')
RESULTS_DIR = ROOT / 'eval' / 'results'


def load_questions(path):
    questions = yaml.safe_load(Path(path).read_text())['questions']
    if len(questions) != 30 or Counter(q['category'] for q in questions) != Counter(
            {category: 5 for category in CATEGORIES}):
        raise ValueError("Expected 30 questions, exactly five in each of six categories")
    if len({q['id'] for q in questions}) != 30:
        raise ValueError("Question IDs must be unique")
    for question in questions:
        expected = question['expected_tools']
        category = question['category']
        if not isinstance(question['question'], str) or not isinstance(expected, list):
            raise ValueError("Questions need text and an expected_tools list")
        if any(tool not in CATEGORIES[:4] for tool in expected) or len(set(expected)) != len(expected):
            raise ValueError("Expected tools must be unique allowlisted names")
        if ((category == 'out_of_scope' and expected)
                or (category == 'multi_tool' and len(expected) != 2)
                or (category in CATEGORIES[:4] and expected != [category])):
            raise ValueError("Expected tools disagree with the question category")
    return questions


def masked_message(error):
    """Redact configured keys and common key forms before reporting errors."""
    message = str(error)
    for name in ('GEMINI_API_KEY', 'GOOGLE_API_KEY', 'OPENAI_API_KEY'):
        key = os.environ.get(name)
        if key:
            message = message.replace(key, '[REDACTED]')
    message = re.sub(r'AIza[\w-]+', '[REDACTED]', message)
    return re.sub(r'(?i)(api[_ -]?key[=:\s]+)[^\s,;]+', r'\1[REDACTED]', message)


def classify_error(error):
    from google.api_core.exceptions import (
        ResourceExhausted, PermissionDenied, Unauthenticated, InvalidArgument, NotFound,
    )
    status = getattr(error, 'status_code', None)
    if status is None:
        status = getattr(getattr(error, 'response', None), 'status_code', None)
    code = getattr(error, 'code', None)
    if callable(code):
        code = code()
    if isinstance(error, ResourceExhausted) or status == 429 or code == 429:
        return 'quota'
    message = str(error).lower()
    if isinstance(error, (PermissionDenied, Unauthenticated)) or (
            isinstance(error, InvalidArgument) and (
                'api_key_invalid' in message or 'api key' in message or 'api_key' in message
                or 'invalid key' in message)):
        return 'auth'
    if isinstance(error, NotFound):
        return 'model_error'
    return 'other'


class ModelCallError(Exception):
    """Only classified, redacted exception information leaves the probe."""
    def __init__(self, outcome, exception_class, message):
        self.outcome = outcome
        super().__init__(f'{exception_class}: {message}')


def enum_name(value):
    """Keep enum names only; never stringify arbitrary provider metadata."""
    name = getattr(value, 'name', None)
    return name if isinstance(name, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) else None


class ResponseProbe:
    """Delegate the response unchanged while recording safe text-access metadata."""
    def __init__(self, response, observation):
        self._response = response
        self._observation = observation
        try:
            block = enum_name(getattr(getattr(response, 'prompt_feedback', None), 'block_reason', None))
            candidates = getattr(response, 'candidates', None)
            finish = enum_name(getattr(candidates[0], 'finish_reason', None)) if candidates else None
            for key, value in (('block_reason', block), ('finish_reason', finish)):
                if value:
                    observation[key] = value
        except Exception:
            # Optional diagnostics must not change the app's response handling.
            pass

    @property
    def text(self):
        try:
            return self._response.text
        except Exception as error:
            self._observation['text_error'] = type(error).__name__
            raise

    def __getattr__(self, name):
        return getattr(self._response, name)


class ModelProbe:
    """Capture provider exceptions that the application catches as fallbacks."""
    def __init__(self, client):
        self.client = client
        self.error = None
        self.responses = []

    def generate_content(self, *args, **kwargs):
        try:
            response = self.client.generate_content(*args, **kwargs)
            observation = {}
            self.responses.append(observation)
            return ResponseProbe(response, observation)
        except Exception as error:
            self.error = ModelCallError(classify_error(error), type(error).__name__,
                                        masked_message(error))
            raise


def live_question(api, question, client, with_answers, observations):
    """Use the real planner/prompt, observing parsed names before fallback/cap."""
    probe = ModelProbe(client)
    original_parse = api.parse_planned_tools
    observation = dict(id=question['id'], category=question['category'], raw_tools=None)

    def observed_parse(text, max_tools=None):
        observation['raw_tools'] = original_parse(text, max_tools=None)
        return original_parse(text, max_tools=max_tools)

    with open(os.devnull, 'w') as sink, patch.object(api, 'get_model', return_value=probe), patch.object(
            api, 'parse_planned_tools', side_effect=observed_parse), redirect_stdout(sink):
        state = api.planner_node(api.AgentState(question['question']))
        if probe.error:
            raise probe.error from None
        raw = observation['raw_tools']
        metadata = probe.responses[0] if probe.responses else {}
        if raw is None and 'text_error' not in metadata:
            raise ModelCallError('other', 'UnobservedParseError', 'Response was not parsed')
        raw_status = 'no_text' if raw is None else ('picked' if raw else 'declined')
        observation.update(metadata, raw_status=raw_status,
                           valid_tool_count=len(raw) if raw is not None else None)
        observation.update(cap_applied=raw is not None and len(raw) > 3,
            monthly_fallback=(not raw and state.selected_tools == ['monthly_revenue']),
            planner_error=None, outcome='ok', failed_calls=0)
        observations.append(observation)
        faithful = None
        if with_answers:
            try:
                state = api.analyst_node(api.compute_node(api.tool_node(state)))
            finally:
                if probe.error:
                    raise probe.error from None
            faithful = numbers_are_grounded(state.final_answer, state.raw_data, state.computed_data)
    return dict(question, got=state.selected_tools, faithful=faithful,
                answer_requested=with_answers, **{key: observation[key] for key in (
                    'raw_tools', 'raw_status', 'valid_tool_count', 'text_error', 'block_reason', 'finish_reason'
                ) if key in observation})


def read_progress(path, questions, api):
    """Validate the raw-status schema; old empty tools cannot reveal lost text errors."""
    latest = {}
    if not Path(path).exists():
        return latest
    ids = {q['id'] for q in questions}
    required = {'id', 'outcome', 'tools', 'raw_status', 'valid_tool_count'}
    optional = {'text_error', 'block_reason', 'finish_reason'}
    for line in Path(path).read_text().splitlines():
        entry = json.loads(line)
        if not isinstance(entry, dict) or not required <= entry.keys():
            raise ValueError('Progress lacks raw observations; archive the old file before a new run')
        raw = entry['tools']
        status = entry['raw_status']
        count = entry['valid_tool_count']
        success = entry['outcome'] == 'ok'
        valid_tools = (isinstance(raw, list) and all(isinstance(t, str) and t in api.TOOLS for t in raw)
                       and len(set(raw)) == len(raw))
        valid_raw = (
            (status == 'no_text' and raw is None and count is None and 'text_error' in entry)
            or (status == 'declined' and valid_tools and raw == [] and type(count) is int and count == 0)
            or (status == 'picked' and valid_tools and bool(raw) and type(count) is int and count == len(raw))
        ) if success else (status is None and raw == [] and count is None)
        if (not set(entry) <= required | optional or entry['id'] not in ids
                or entry['outcome'] not in ('ok', 'quota', 'auth', 'model_error', 'other')
                or not valid_raw
                or any(not isinstance(entry[k], str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', entry[k])
                       for k in optional if k in entry)
                or ('text_error' in entry and status != 'no_text')):
            raise ValueError('Invalid live progress entry; archive the file before a new run')
        latest[entry['id']] = entry
    return latest


def append_progress(path, question_id, observation):
    """Only persist allowlisted tools, raw status/count and safe metadata names."""
    entry = dict(id=question_id, outcome=observation['outcome'],
                 tools=observation.get('raw_tools', []), raw_status=observation.get('raw_status'),
                 valid_tool_count=observation.get('valid_tool_count'))
    for key in ('text_error', 'block_reason', 'finish_reason'):
        if key in observation:
            entry[key] = observation[key]
    with Path(path).open('a') as stream:
        stream.write(json.dumps(entry) + '\n')


def run_questions(api, questions, *, client=None, with_answers=False, delay=2, sleep=time.sleep,
                  progress_path=None, resume=False):
    """A missing client selects offline keyword-only evaluation, never planner_node."""
    rows, observations = [], []
    stopped = None
    completed = read_progress(progress_path, questions, api) if resume and progress_path else {}
    skipped = sum(completed.get(q['id'], {}).get('outcome') == 'ok' for q in questions)
    if resume:
        print(f'Resume: skipped {skipped} completed questions')
    for question in questions:
        saved = completed.get(question['id'])
        if client is not None and saved and saved['outcome'] == 'ok':
            raw = saved['tools']
            selected = (['monthly_revenue'] if saved['raw_status'] == 'no_text'
                        else raw[:3] or api.keyword_fallback(question['question']))
            raw_fields = {key: saved[key] for key in (
                'raw_status', 'valid_tool_count', 'text_error', 'block_reason', 'finish_reason'
            ) if key in saved}
            rows.append(dict(question, got=selected, faithful=None, answer_requested=False,
                             raw_tools=raw, **raw_fields))
            observations.append(dict(id=question['id'], category=question['category'],
                raw_tools=raw, cap_applied=raw is not None and len(raw) > 3,
                monthly_fallback=not raw and selected == ['monthly_revenue'],
                planner_error=None, outcome='ok', failed_calls=0, **raw_fields))
    calls_started = False
    for question in questions:
        if client is not None and completed.get(question['id'], {}).get('outcome') == 'ok':
            continue
        if client is None:
            rows.append(dict(question, got=api.keyword_fallback(question['question']),
                             faithful=None, answer_requested=False))
            continue
        if calls_started:
            sleep(delay)
        calls_started = True
        for attempt in range(2):
            before = len(observations)
            try:
                row = live_question(api, question, client, with_answers, observations)
                rows.append(row)
                break
            except ModelCallError as error:
                del observations[before:]
                observations.append(dict(id=question['id'], category=question['category'],
                    outcome=error.outcome, failed_calls=1,
                    cap_applied=False, monthly_fallback=False, planner_error=str(error)))
                print(f'{question["id"]}: {error.outcome}: {error}')
                if error.outcome in ('quota', 'auth', 'model_error'):
                    stopped = str(error)
                    break
                if attempt == 0:
                    sleep(delay)
        if progress_path:
            result = observations[-1]
            append_progress(progress_path, question['id'], result)
        if stopped:
            break
    return rows, observations, stopped


def format_rate(successes, n):
    bounds = wilson(successes, n)
    if bounds is None:
        return 'not measured (n=0)'
    low, high = bounds
    return f'{successes / n:.1%} (95% Wilson {low:.1%}–{high:.1%}; n={n})'


def render_report(questions, rows, observations, mode, stopped, with_answers, model_name=None):
    scores = [selection_scores(row['expected_tools'], row['got']) for row in rows]
    n = len(rows)
    successful = [o for o in observations if o.get('outcome', 'ok') == 'ok']
    failed_calls = sum(o.get('failed_calls', 0) for o in observations)
    attempted = {o['id'] for o in observations} | {r['id'] for r in rows}
    lines = ['# Agent evaluation', '', f'Mode: **{mode}**; {n} of {len(questions)} questions completed.',
        f'Model: {model_name}' if mode == 'live' else 'Model: none (keyword_fallback only)',
        'Labels are a DRAFT that a human must review.', '']
    if mode == 'live' and n < len(questions):
        lines.insert(2, f'**PARTIAL: {n} of {len(questions)} questions evaluated**')
    if mode == 'offline':
        lines += ['**Live planner accuracy: pending first live run.**',
                  'This run evaluates only keyword_fallback; no planner or analyst was called.', '']
    if stopped:
        lines += [f'Stopped cleanly on {stopped}; completed questions: {n}.', '']
    metric_labels = (
        ('keyword_fallback baseline (not the LLM): exact-match tool selection',
         'keyword_fallback baseline (not the LLM): mean precision',
         'keyword_fallback baseline (not the LLM): mean recall')
        if mode == 'offline' else
        ('Exact-match tool-selection accuracy', 'Mean per-question precision', 'Mean per-question recall')
    )
    metric_labels = tuple(label + ' (final tools after app fallback and cap)' for label in metric_labels)
    lines += ['| Metric | Result |', '| --- | --- |']
    if mode == 'live' and n == 0:
        lines += ['| Planner evaluation | no valid planner responses |']
    else:
        lines += [
            f"| {metric_labels[0]} | {format_rate(sum(s['exact'] for s in scores), n)} |",
            f"| {metric_labels[1]} | {format_rate(sum(s['precision'] for s in scores), n)} |",
            f"| {metric_labels[2]} | {format_rate(sum(s['recall'] for s in scores), n)} |"]
    observed_oos = [o for o in successful if o['category'] == 'out_of_scope']
    for status, label in (('declined', 'model declined'), ('picked', 'model picked tools'),
                          ('no_text', 'no usable response')):
        count = sum(o['raw_status'] == status for o in observed_oos)
        result = f'{count} of {len(observed_oos)}' if mode == 'live' else 'not measured (offline)'
        lines.append(f'| Out-of-scope: {label} | {result} |')
    for status, label in (
        ('declined', 'Final tools came from keyword fallback after the model declined'),
        ('no_text', 'Final tools came from keyword fallback after no usable response'),
        ('no_text', 'Questions with no usable model text'),
    ):
        count = sum(o['raw_status'] == status for o in successful)
        result = f'{count} of {n}' if mode == 'live' else 'not measured (offline)'
        lines.append(f'| {label} | {result} |')
    lines += [f"| Three-tool cap applied | {format_rate(sum(o['cap_applied'] for o in successful), len(successful))} |"]
    if observations:
        lines += [f"| Questions with cap applied (count) | {sum(o['cap_applied'] for o in successful)} of {len(successful)} |",
                  f"| Planner errors (count) | {failed_calls} |"]
    if mode == 'live':
        lines += [f'| Failed calls (count) | {failed_calls} |',
                  f'| Questions not run (count) | {len(questions) - len(attempted)} |']
    if mode == 'offline':
        defaults = sum(row['got'] == ['monthly_revenue'] for row in rows)
        lines += [f'| Keyword fallback returned monthly_revenue (not a model observation) | {format_rate(defaults, n)} |']
    if with_answers:
        assessed = [r for r in rows if r['faithful'] is not None]
        lines += [f"| All $/% figures traceable (heuristic) | {format_rate(sum(r['faithful'] for r in assessed), len(assessed))} |",
                  f"| Answers without $/% figures (excluded, count) | {n - len(assessed)} |"]
    lines += ['', 'Macro precision/recall bounds use fractional effective successes and are descriptive Wilson-style bounds, not binomial confidence guarantees.',
        'Tool order is ignored for accuracy; empty/empty scores 1, and an empty/nonempty mismatch scores 0.', '',
        '| Category | Correct (final tools after app fallback and cap) | Completed |', '| --- | --- | --- |']
    for category in CATEGORIES:
        selected = [r for r in rows if r['category'] == category]
        correct = sum(selection_scores(r['expected_tools'], r['got'])['exact'] for r in selected)
        denominator = len(selected) if mode == 'live' else 5
        lines.append(f'| {category} | {correct} of {denominator} | {len(selected)} |')
    lines += ['', '| ID | Expected | Model raw | Got (final) | Response metadata | Pass/fail |',
              '| --- | --- | --- | --- | --- | --- |']
    completed = {row['id']: row for row in rows}
    for question in questions:
        row = completed.get(question['id'])
        expected = ', '.join(question['expected_tools']) or '[]'
        failed = question['id'] in attempted and not row
        got = (', '.join(row['got']) or '[]') if row else ('call failed' if failed else 'not completed')
        outcome = ('PASS' if selection_scores(question['expected_tools'], row['got'])['exact'] else 'FAIL') if row else ('CALL FAILED' if failed else 'NOT RUN')
        if mode == 'offline':
            raw_display = 'not measured (offline)'
        elif not row:
            raw_display = 'call failed' if failed else 'not run'
        elif row['raw_status'] == 'no_text':
            raw_display = 'no text'
        else:
            raw_display = ', '.join(row['raw_tools']) or '[]'
        metadata = '; '.join(f'{key}={row[key]}' for key in (
            'valid_tool_count', 'text_error', 'block_reason', 'finish_reason'
        ) if row and key in row and row[key] is not None) or 'none'
        lines.append(f"| {question['id']} | {expected} | {raw_display} | {got} | {metadata} | {outcome} |")
    return '\n'.join(lines) + '\n'


def write_report(report, *, live=False, output=None):
    """Keep default outputs in results; external destinations require opt-in."""
    destination = (Path(output).expanduser() if output is not None else
                   RESULTS_DIR / ('latest.md' if live else 'latest_offline.md'))
    if output is None and not destination.resolve().is_relative_to(RESULTS_DIR.absolute()):
        raise ValueError('Default output must stay in eval/results; use --output for an explicit path')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(report)
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--offline', action='store_true', help='Keyword fallback only (default)')
    mode.add_argument('--live', action='store_true', help='Real planner; consumes Gemini calls')
    parser.add_argument('--output', type=Path, help='Explicit report path, including outside eval/results')
    parser.add_argument('--resume', action='store_true', help='Live only: skip completed progress IDs')
    parser.add_argument('--with-answers', action='store_true', help='Live only: call tools/analyst and check numbers')
    parser.add_argument('--delay', type=float, default=2, help='Seconds between live questions (default: 2)')
    args = parser.parse_args(argv)
    if args.resume and not args.live:
        parser.error('--resume requires --live')
    if args.with_answers and not args.live:
        parser.error('--with-answers requires --live')
    if args.delay <= 0:
        parser.error('--delay must be positive')
    if args.live and not os.environ.get('GEMINI_API_KEY'):
        parser.error('--live requires GEMINI_API_KEY in the environment; .env is not loaded')
    os.environ['PYTHON_DOTENV_DISABLED'] = '1'
    if not args.live:
        runpy.run_path(str(ROOT / 'scripts/offline_guard/sitecustomize.py'))
    from api import main as api
    questions = load_questions(Path(__file__).with_name('questions.yaml'))
    with tempfile.TemporaryDirectory(prefix='agent-eval-') as directory:
        database = build_database(directory)
        with patch.object(api, 'DB_PATH', database):
            client = api.get_model() if args.live else None
            rows, observations, stopped = run_questions(api, questions, client=client,
                with_answers=args.with_answers, delay=args.delay, resume=args.resume,
                progress_path=Path(__file__).with_name('results') / 'live_progress.jsonl' if args.live else None)
    report = render_report(questions, rows, observations,
                           'live' if args.live else 'offline', stopped, args.with_answers,
                           model_name=api.get_model_name() if args.live else None)
    write_report(report, live=args.live, output=args.output)
    print(report, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
