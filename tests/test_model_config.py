"""Model configuration checks without creating a provider client."""

from api.main import get_model_name


def test_model_name_default_and_environment_override(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert get_model_name() == "gemini-3.5-flash-lite"
    monkeypatch.setenv("GEMINI_MODEL", "custom-gemini-model")
    assert get_model_name() == "custom-gemini-model"
