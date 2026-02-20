"""Application-wide configuration powered by pydantic-settings.

Loads environment variables from .env once and provides typed,
centralised access to paths, API keys, and tuning parameters.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# The project root is two levels above chasm/core/config.py
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Global settings for the Chasm application."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Application metadata ----
    app_name: str = "Chasm"
    version: str = "0.1.0"
    debug: bool = False

    # ---- Paths (derived from project root) ----
    project_root: Path = _PROJECT_ROOT
    data_dir: Path = _PROJECT_ROOT
    raw_data_dir: Path = _PROJECT_ROOT / "chasm" / "data" / "raw"
    reports_dir: Path = _PROJECT_ROOT / "chasm" / "reports"

    # ---- LLM ----
    google_api_key: str = ""
    gemini_model: str = "gemini-3-pro-preview"

    # ---- Reddit ----
    reddit_client_id: str = "YOUR_ID"
    reddit_client_secret: str = "YOUR_SECRET"
    reddit_user_agent: str = "chasm_proto"

    # ---- Embeddings ----
    embedding_model: str = "all-MiniLM-L6-v2"
    similarity_threshold: float = 0.75

    # ---- CORS ----
    cors_origins: str = ""

    @property
    def export_path(self) -> Path:
        return self.data_dir / "export.json"


settings = Settings()
