from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite:///./kindergarten.db"
    jwt_secret: str = "development-only-change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 720
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    upload_dir: str = "./uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()
