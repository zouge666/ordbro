"""Settings loading.

Settings live in ``config/ordbro.toml``. Every value has a default, so the
file only needs the keys you want to change. Unknown keys raise an error,
which catches typos early.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(os.environ.get("ORDBRO_HOME", Path(__file__).resolve().parents[2]))
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "ordbro.toml"


class ConfigError(ValueError):
    """Raised when the settings file is invalid."""


@dataclass
class AppSettings:
    host: str = "127.0.0.1"
    port: int = 8000
    data_dir: str = "data"
    state_dir: str = "var"
    web_dir: str = "web"


@dataclass
class RagSettings:
    preset: str = "ordbro"
    top_k: int = 5
    rrf_k: int = 60
    abstain_below: float = 0.095


@dataclass
class LLMSettings:
    provider: str = "none"
    model: str = ""
    base_url: str = ""
    api_key_env: str = "ORDBRO_LLM_API_KEY"
    timeout: float = 20.0

    @property
    def enabled(self) -> bool:
        return self.provider != "none"

    @property
    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "")


@dataclass
class Settings:
    app: AppSettings = field(default_factory=AppSettings)
    rag: RagSettings = field(default_factory=RagSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)
    root: Path = PROJECT_ROOT

    def resolve(self, relative: str | Path) -> Path:
        path = Path(relative)
        return path if path.is_absolute() else self.root / path

    @property
    def data_path(self) -> Path:
        return self.resolve(self.app.data_dir)

    @property
    def state_path(self) -> Path:
        return self.resolve(self.app.state_dir)

    @property
    def web_path(self) -> Path:
        return self.resolve(self.app.web_dir)


_SECTIONS = {"app": AppSettings, "rag": RagSettings, "llm": LLMSettings}


def load_settings(path: str | Path | None = None, root: Path | None = None) -> Settings:
    """Load settings from a TOML file. A missing default file gives defaults."""
    config_path = Path(path or os.environ.get("ORDBRO_CONFIG", DEFAULT_CONFIG))
    raw: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open("rb") as handle:
            raw = tomllib.load(handle)
    elif path is not None:
        raise ConfigError(f"config file not found: {config_path}")

    settings = Settings(root=root or PROJECT_ROOT)
    for name, values in raw.items():
        if name not in _SECTIONS:
            raise ConfigError(f"unknown config section: [{name}]")
        if not isinstance(values, dict):
            raise ConfigError(f"[{name}] must be a table")
        setattr(settings, name, _build(_SECTIONS[name], values, name))
    _validate(settings)
    return settings


def _build(cls: type, values: dict[str, Any], section: str) -> Any:
    allowed = {f.name: f for f in fields(cls)}
    kwargs: dict[str, Any] = {}
    for key, value in values.items():
        if key not in allowed:
            raise ConfigError(f"unknown key in [{section}]: {key}")
        default = allowed[key].default
        if isinstance(default, float) and isinstance(value, int):
            value = float(value)
        if not isinstance(value, type(default)) or isinstance(value, bool) != isinstance(
            default, bool
        ):
            raise ConfigError(f"[{section}] {key} must be {type(default).__name__}")
        kwargs[key] = value
    return cls(**kwargs)


def _validate(settings: Settings) -> None:
    if settings.rag.top_k <= 0:
        raise ConfigError("[rag] top_k must be positive")
    if settings.rag.rrf_k <= 0:
        raise ConfigError("[rag] rrf_k must be positive")
    if not 0.0 <= settings.rag.abstain_below <= 1.0:
        raise ConfigError("[rag] abstain_below must be between 0 and 1")
    if settings.llm.provider not in {"none", "openai-compatible"}:
        raise ConfigError("[llm] provider must be 'none' or 'openai-compatible'")
