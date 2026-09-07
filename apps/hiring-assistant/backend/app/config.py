from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hunar_api_key: str = ""
    hunar_webhook_secondary_keys: str = ""  # comma separated, for key rotation
    database_url: str = "sqlite:///./hiring_assistant.db"
    default_voice_persona: str = "NEHA"
    default_language: str = "ENGLISH"
    default_timezone: str = "Asia/Kolkata"
    cors_origins: str = "http://localhost:3000"
    public_base_url: str = ""  # e.g. https://hiring-assistant-api.onrender.com (used for webhook callback urls)
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    auth_required: bool = True
    pii_encryption_key: str = ""
    rate_limit: str = "30/minute"
    queue_backend: str = "local"
    redis_url: str = "redis://localhost:6379/0"
    sentry_dsn: str = ""
    auto_create_schema: bool = False
    anthropic_api_key: str = ""
    llm_model: str = "claude-3-5-sonnet-20241022"

    @property
    def trusted_webhook_keys(self) -> list[str]:
        keys = [self.hunar_api_key] if self.hunar_api_key else []
        keys += [k.strip() for k in self.hunar_webhook_secondary_keys.split(",") if k.strip()]
        return keys

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
