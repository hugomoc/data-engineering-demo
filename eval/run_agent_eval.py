"""Evaluate draft question labels on a disposable fixture; offline by default."""

import argparse
from collections import Counter
from contextlib import redirect_stdout
import io
import os
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


class ModelProbe:
    """Observe quota errors the application deliberately catches as fallbacks."""
    def __init__(self, client):
        self.client = client
        self.quota = None
        self.error = None

    def generate_content(self, *args, **kwargs):
        from google.api_core.exceptions import ResourceExhausted
        try:
            return self.client.generate_content(*args, **kwargs)
        except ResourceExhausted as error:
            self.quota = error
            raise
        except Exception as error:
            self.error = type(error).__name__
            raise


def live_question(api, question, client, with_answers, observations):
    """Use the real planner/prompt, observing parsed names before fallback/cap."""
    probe = ModelProbe(client)
    original_parse = api.parse_planned_tools
    observation = dict(id=question['id'], category=question['category'], raw_tools=None)

    def observed_parse(text, max_tools=None):
        observation['raw_tools'] = original_parse(text, max_tools=None)
        return original_parse(text, max_tools=max_tools)

    with patch.object(api, 'get_model', return_value=probe), patch.object(
            api, 'parse_planned_tools', side_effect=observed_parse), redirect_stdout(io.StringIO()):
        state = api.planner_node(api.AgentState(question['question']))
        if probe.quota:
            raise probe.quota
        raw = observation['raw_tools']
        observation.update(cap_applied=raw is not None and len(raw) > 3,
            monthly_fallback=(not raw and state.selected_tools == ['monthly_revenue']),
            planner_error=probe.error)
        observations.append(observation)
        faithful = None
        if with_answers:
            state = api.analyst_node(api.compute_node(api.tool_node(state)))
            if probe.quota:
                raise probe.quota
            faithful = numbers_are_grounded(state.final_answer, state.raw_data, state.computed_data)
    return dict(question, got=state.selected_tools, faithful=faithful,
                answer_requested=with_answers)


def run_questions(api, questions, *, client=None, with_answers=False, delay=2, sleep=time.sleep):
    """A missing client selects offline keyword-only evaluation, never planner_node."""
    from google.api_core.exceptions import ResourceExhausted
    rows, observations = [], []
    stopped = None
    for index, question in enumerate(questions):
        if client is not None and index:
            sleep(delay)
        try:
            if client is None:
                row = dict(question, got=api.keyword_fallback(question['question']),
                           faithful=None, answer_requested=False)
            else:
                row = live_question(api, question, client, with_answers, observations)
            rows.append(row)
        except ResourceExhausted:
            stopped = 'ResourceExhausted'
            break
    return rows, observations, stopped


def format_rate(successes, n):
    bounds = wilson(successes, n)
    if bounds is None:
        return 'not measured (n=0)'
    low, high = bounds
    return f'{successes / n:.1%} (95% Wilson {low:.1%}–{high:.1%}; n={n})'


def render_report(questions, rows, observations, mode, stopped, with_answers):
    scores = [selection_scores(row['expected_tools'], row['got']) for row in rows]
    n = len(rows)
    lines = ['# Agent evaluation', '', f'Mode: **{mode}**; {n} of {len(questions)} questions completed.',
        'Labels are a DRAFT that a human must review.', '']
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
    lines += ['| Metric | Result |', '| --- | --- |',
        f"| {metric_labels[0]} | {format_rate(sum(s['exact'] for s in scores), n)} |",
        f"| {metric_labels[1]} | {format_rate(sum(s['precision'] for s in scores), n)} |",
        f"| {metric_labels[2]} | {format_rate(sum(s['recall'] for s in scores), n)} |"]
    observed_oos = [o for o in observations if o['category'] == 'out_of_scope' and o['raw_tools'] is not None]
    lines += [f"| Model selected no valid tool on out-of-scope input, before fallback | {format_rate(sum(not o['raw_tools'] for o in observed_oos), len(observed_oos))} |",
        f"| Silent monthly_revenue fallback | {format_rate(sum(o['monthly_fallback'] for o in observations), len(observations))} |",
        f"| Three-tool cap applied | {format_rate(sum(o['cap_applied'] for o in observations), len(observations))} |"]
    if observations:
        lines += [f"| Questions with cap applied (count) | {sum(o['cap_applied'] for o in observations)} of {len(observations)} |",
                  f"| Planner errors (count) | {sum(bool(o['planner_error']) for o in observations)} |"]
    if mode == 'offline':
        defaults = sum(row['got'] == ['monthly_revenue'] for row in rows)
        lines += [f'| Keyword fallback returned monthly_revenue (not a model observation) | {format_rate(defaults, n)} |']
    if with_answers:
        assessed = [r for r in rows if r['faithful'] is not None]
        lines += [f"| All $/% figures traceable (heuristic) | {format_rate(sum(r['faithful'] for r in assessed), len(assessed))} |",
                  f"| Answers without $/% figures (excluded, count) | {n - len(assessed)} |"]
    lines += ['', 'Macro precision/recall bounds use fractional effective successes and are descriptive Wilson-style bounds, not binomial confidence guarantees.',
        'Tool order is ignored for accuracy; empty/empty scores 1, and an empty/nonempty mismatch scores 0.', '',
        '| Category | Correct | Completed |', '| --- | --- | --- |']
    for category in CATEGORIES:
        selected = [r for r in rows if r['category'] == category]
        correct = sum(selection_scores(r['expected_tools'], r['got'])['exact'] for r in selected)
        lines.append(f'| {category} | {correct} of 5 | {len(selected)} |')
    lines += ['', '| ID | Expected | Got | Pass/fail |', '| --- | --- | --- | --- |']
    completed = {row['id']: row for row in rows}
    for question in questions:
        row = completed.get(question['id'])
        expected = ', '.join(question['expected_tools']) or '[]'
        got = (', '.join(row['got']) or '[]') if row else 'not completed'
        outcome = ('PASS' if selection_scores(question['expected_tools'], row['got'])['exact'] else 'FAIL') if row else 'NOT RUN'
        lines.append(f"| {question['id']} | {expected} | {got} | {outcome} |")
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--offline', action='store_true', help='Keyword fallback only (default)')
    mode.add_argument('--live', action='store_true', help='Real planner; consumes Gemini calls')
    parser.add_argument('--with-answers', action='store_true', help='Live only: call tools/analyst and check numbers')
    parser.add_argument('--delay', type=float, default=2, help='Seconds between live questions (default: 2)')
    args = parser.parse_args(argv)
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
                with_answers=args.with_answers, delay=args.delay)
    report = render_report(questions, rows, observations,
                           'live' if args.live else 'offline', stopped, args.with_answers)
    destination = Path(__file__).with_name('results') / 'latest.md'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(report)
    print(report, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
