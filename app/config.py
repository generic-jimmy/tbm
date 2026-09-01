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

    # ── Webhook mode ────────────────────────────────────────────────────────
    # If set, e.g. https://tbm.yourapp.com, bots register a Telegram webhook
    # at {webhook_base_url}/webhook/{bot_hash} instead of long-polling.
    # Leave empty to keep polling (default — works without a public HTTPS URL,
    # e.g. local dev). Webhooks and polling are mutually exclusive per bot.
    webhook_base_url: str = ""

    # ── Scheduled MTProto re-sync ───────────────────────────────────────────
    # Hours between automatic incremental re-syncs of every known chat for
    # every active bot with MTProto configured. 0 disables it.
    resync_interval_hours: float = 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
