"""Report destinations use temporary paths and fake models, never live calls."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from api import main as api
from eval import run_agent_eval as evaluation


@pytest.fixture
def results_dir(tmp_path, monkeypatch):
    directory = tmp_path / 'eval' / 'results'
    directory.mkdir(parents=True)
    monkeypatch.setattr(evaluation, 'RESULTS_DIR', directory)
    return directory


def test_offline_cli_preserves_live_report(results_dir, tmp_path, monkeypatch):
    latest = results_dir / 'latest.md'
    original = b'# Stored live results\n\nDo not replace.\n'
    latest.write_bytes(original)
    monkeypatch.setattr(evaluation, 'build_database', lambda directory: tmp_path / 'unused-fixture.duckdb')
    no_model = Mock(side_effect=AssertionError('Offline must not initialize a model'))
    monkeypatch.setattr(api, 'get_model', no_model)
    assert evaluation.main(['--offline']) == 0
    assert latest.read_bytes() == original
    offline = results_dir / 'latest_offline.md'
    assert 'Mode: **offline**; 30 of 30 questions completed.' in offline.read_text()
    assert 'Model: none (keyword_fallback only)' in offline.read_text()
    no_model.assert_not_called()


def test_fake_live_model_report_uses_latest(results_dir):
    # Exercise the live runner/writer path with an injected model, never --live.
    question = dict(id='Q01', question='Top products?', category='top_products', expected_tools=['top_products'])
    fake = SimpleNamespace(generate_content=Mock(return_value=SimpleNamespace(text='top_products')))
    rows, observations, stopped = evaluation.run_questions(api, [question], client=fake)
    report = evaluation.render_report([question], rows, observations, 'live', stopped, False,
                                      model_name='fake-model')
    destination = evaluation.write_report(report, live=True)
    assert destination == results_dir / 'latest.md'
    assert destination.read_text() == report
    assert 'Model: fake-model' in destination.read_text()
    assert not (results_dir / 'latest_offline.md').exists()
    fake.generate_content.assert_called_once()


@pytest.mark.parametrize('live', [False, True])
def test_explicit_output_overrides_either_mode(results_dir, tmp_path, live):
    live_file = results_dir / 'latest.md'
    live_file.write_bytes(b'original live report')
    destination = tmp_path / 'explicit' / 'report.md'
    assert evaluation.write_report('custom report', live=live, output=destination) == destination
    assert destination.read_text() == 'custom report'
    assert live_file.read_bytes() == b'original live report'
    assert not (results_dir / 'latest_offline.md').exists()


def test_offline_cli_output_argument_is_forwarded(results_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(evaluation, 'build_database', lambda directory: tmp_path / 'unused-fixture.duckdb')
    destination = tmp_path / 'explicit-cli.md'
    assert evaluation.main(['--offline', '--output', str(destination)]) == 0
    assert 'Mode: **offline**' in destination.read_text()
    assert list(results_dir.iterdir()) == []


@pytest.mark.parametrize('live,filename', [(False, 'latest_offline.md'), (True, 'latest.md')])
def test_implicit_output_cannot_escape_through_file_symlink(results_dir, tmp_path, live, filename):
    external = tmp_path / 'external.md'
    external.write_bytes(b'untouched')
    (results_dir / filename).symlink_to(external)
    with pytest.raises(ValueError, match='use --output'):
        evaluation.write_report('replacement', live=live)
    assert external.read_bytes() == b'untouched'


def test_implicit_results_directory_symlink_is_refused(tmp_path, monkeypatch):
    external = tmp_path / 'external'
    external.mkdir()
    results = tmp_path / 'results-link'
    results.symlink_to(external, target_is_directory=True)
    monkeypatch.setattr(evaluation, 'RESULTS_DIR', results)
    with pytest.raises(ValueError, match='use --output'):
        evaluation.write_report('replacement')
    assert list(external.iterdir()) == []
