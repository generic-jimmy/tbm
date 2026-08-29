from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    supabase_url: str = ""
    supabase_service_key: str = ""
    secret_key: str
    admin_password: str
    port: int = 8000
    log_level: str = "INFO"
    jwt_expire_hours: int = 168
    auto_forward_files: bool = True
    history_drain_on_boot: bool = True
    poll_interval_seconds: float = 0.8
    # MTProto — from my.telegram.org (free, one-time setup)
    telegram_api_id: int = 0
    telegram_api_hash: str = ""

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
