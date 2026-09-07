from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hunar_api_key: str = ""
    hunar_webhook_secondary_keys: str = ""
    pdl_api_key: str = ""
    pdl_mock_mode: bool = True
    database_url: str = "sqlite:///./people_search.db"
    default_voice_persona: str = "NEHA"
    default_language: str = "ENGLISH"
    default_timezone: str = "Asia/Kolkata"
    cors_origins: str = "http://localhost:3000"
    public_base_url: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "claude-3-5-sonnet-20241022"
    google_service_account_json: str = ""
    google_calendar_id: str = "primary"

    @property
    def trusted_webhook_keys(self) -> list[str]:
        keys = [self.hunar_api_key] if self.hunar_api_key else []
        keys += [k.strip() for k in self.hunar_webhook_secondary_keys.split(",") if k.strip()]
        return keys

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_mock_mode(self) -> bool:
        return self.pdl_mock_mode or not self.pdl_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
