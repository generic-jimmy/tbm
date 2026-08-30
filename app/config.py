"""Application settings — pydantic-settings v2 style."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Required ──────────────────────────────────────────────────────────────
    database_url:   str
    secret_key:     str          # used for Fernet token encryption + JWT signing
    admin_password: str

    # ── Optional integrations ──────────────────────────────────────────────────
    supabase_url:        str = ""
    supabase_service_key: str = ""

    # ── Telegram MTProto (free from https://my.telegram.org) ──────────────────
    telegram_api_id:   int = 0
    telegram_api_hash: str = ""

    # ── Tunable defaults ───────────────────────────────────────────────────────
    port:                     int   = 8000
    log_level:                str   = "INFO"
    jwt_expire_hours:         int   = 168      # 7 days
    auto_forward_files:       bool  = True
    history_drain_on_boot:    bool  = True
    poll_interval_seconds:    float = 0.8


@lru_cache
def get_settings() -> Settings:
    return Settings()
