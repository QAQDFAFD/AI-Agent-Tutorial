from pathlib import Path

from tutor.config import Settings


def test_settings_defaults_and_env_mapping(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("TUTOR_EMBEDDING_MODEL", "test-embed")
    settings = Settings(_env_file=None)
    assert settings.openai_model == "test-model"
    assert settings.tutor_embedding_model == "test-embed"
    assert settings.docs_dir == Path("docs")
    assert settings.top_k == 4
