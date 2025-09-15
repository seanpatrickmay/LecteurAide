from pydantic import BaseSettings, AnyUrl
from functools import lru_cache

class Settings(BaseSettings):
    supabase_url: AnyUrl
    supabase_anon_key: str
    supabase_service_role_key: str
    openai_api_key: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    redis_url: AnyUrl | str = "redis://localhost:6379/0"
    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
