"""Central configuration for the NEX backend.

All secrets are read from environment variables (never committed).
"""
from __future__ import annotations

import os
from functools import lru_cache


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


class Settings:
    """Application settings resolved from the environment."""

    # --- Gemini -------------------------------------------------------
    gemini_api_key: str = _env("GEMINI_API_KEY")
    # Primary + fallback models. The first model that answers is used.
    gemini_model: str = _env("GEMINI_MODEL", "gemini-3.6-flash")
    gemini_fallback_models: tuple[str, ...] = tuple(
        m.strip()
        for m in _env(
            "GEMINI_FALLBACK_MODELS",
            "gemini-3.5-flash-lite,gemini-3.8-flash",
        ).split(",")
        if m.strip()
    )

    request_timeout: float = _env_float("GEMINI_TIMEOUT", 45.0)
    max_output_tokens: int = _env_int("GEMINI_MAX_OUTPUT_TOKENS", 512)
    temperature: float = _env_float("GEMINI_TEMPERATURE", 0.9)

    # --- Server -------------------------------------------------------
    app_name: str = "NEX AI Robot Pet API"
    version: str = "1.0.0"
    cors_origins: str = _env("CORS_ORIGINS", "*")

    # --- School knowledge --------------------------------------------
    school_url: str = _env("SCHOOL_URL", "https://montfortbagaha.org/")
    school_cache_ttl: int = _env_int("SCHOOL_CACHE_TTL", 3600)

    # --- Weather (Open-Meteo: free, no API key required) --------------
    weather_enabled: bool = _env("WEATHER_ENABLED", "1") not in ("0", "false", "False")

    # --- Runtime ------------------------------------------------------
    log_level: str = _env("LOG_LEVEL", "INFO")
    history_turns: int = _env_int("HISTORY_TURNS", 8)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def allowed_origins(self) -> list[str]:
        if self.cors_origins.strip() in ("", "*"):
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
