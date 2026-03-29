"""
app/config/settings.py
Centralised application settings loaded from .env via pydantic-settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
import os


class Settings(BaseSettings):
    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = Field(default="Supply Chain AI Agent")
    app_env: str = Field(default="development")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    debug: bool = Field(default=True)

    # ── Risk / Decision Thresholds ───────────────────────────────────────────
    risk_threshold: int = Field(default=60)
    max_cost_threshold: float = Field(default=150000.0)
    sla_max_delay_days: int = Field(default=7)
    max_allowed_cost_multiplier: float = Field(default=1.30)
    min_confidence_score: float = Field(default=0.75)

    # ── File Paths ───────────────────────────────────────────────────────────
    audit_log_path: str = Field(default="logs/audit_logs.json")
    system_log_path: str = Field(default="logs/system_logs.log")
    suppliers_csv: str = Field(default="data/suppliers.csv")
    routes_csv: str = Field(default="data/routes.csv")
    shipments_csv: str = Field(default="data/shipments.csv")

    # ── External API Keys ────────────────────────────────────────────────────
    weather_api_key: str = Field(default=os.getenv("WEATHER_API_KEY", ""))
    llm_api_key: str = Field(default=os.getenv("LLM_API_KEY", ""))

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
