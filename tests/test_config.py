"""Settings parsing — guards the AUTO48_CORS_ORIGINS env regression.

A comma-separated env value must parse to a list. Without NoDecode,
pydantic-settings JSON-decodes list fields and crashes on a plain string
(SettingsError) before the validator runs — which would break startup in any
environment that sets AUTO48_CORS_ORIGINS (e.g. production).
"""

from auto48.config import Settings


def test_cors_origins_default_is_list():
    s = Settings(_env_file=None)
    assert isinstance(s.cors_origins, list)
    assert "http://localhost:3000" in s.cors_origins


def test_cors_origins_csv_env_parses_to_list(monkeypatch):
    monkeypatch.setenv("AUTO48_CORS_ORIGINS", "https://kekec.ee, https://www.kekec.ee")
    s = Settings(_env_file=None)
    assert s.cors_origins == ["https://kekec.ee", "https://www.kekec.ee"]


def test_cors_origins_single_value_env(monkeypatch):
    monkeypatch.setenv("AUTO48_CORS_ORIGINS", "https://kekec.ee")
    s = Settings(_env_file=None)
    assert s.cors_origins == ["https://kekec.ee"]
