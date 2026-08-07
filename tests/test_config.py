from pathlib import Path

import pytest

from ordbro.config import ConfigError, load_settings


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "ordbro.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_default_file_loads():
    settings = load_settings()
    assert settings.rag.preset == "ordbro"
    assert settings.rag.abstain_below == 0.095
    assert settings.llm.enabled is False
    assert settings.data_path.name == "data"


def test_partial_file_keeps_defaults(tmp_path):
    settings = load_settings(write(tmp_path, "[rag]\ntop_k = 3\n"), root=tmp_path)
    assert settings.rag.top_k == 3
    assert settings.rag.rrf_k == 60
    assert settings.state_path == tmp_path / "var"


def test_int_is_accepted_for_float(tmp_path):
    settings = load_settings(write(tmp_path, "[rag]\nabstain_below = 0\n"))
    assert settings.rag.abstain_below == 0.0


@pytest.mark.parametrize(
    "text",
    [
        "[nope]\nx = 1\n",
        "[rag]\ntopk = 3\n",
        "[rag]\ntop_k = 'three'\n",
        "[rag]\ntop_k = 0\n",
        "[llm]\nprovider = 'magic'\n",
    ],
)
def test_bad_values_raise(tmp_path, text):
    with pytest.raises(ConfigError):
        load_settings(write(tmp_path, text))


def test_missing_explicit_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_settings(tmp_path / "missing.toml")
