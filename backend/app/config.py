from functools import lru_cache

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
    )

    app_name: str = Field(default="LecteurAide Backend", alias="LECTEUR_APP_NAME")
    database_url: str = Field(default="sqlite:///./lecteur_aide.db", alias="LECTEUR_DATABASE_URL")

    google_project_id: str | None = Field(default=None, alias="LECTEUR_GOOGLE_PROJECT_ID")
    google_location: str = Field(default="global", alias="LECTEUR_GOOGLE_LOCATION")
    vertex_location: str = Field(default="us-central1", alias="LECTEUR_VERTEX_LOCATION")
    google_credentials_path: str | None = Field(default=None, alias="LECTEUR_GOOGLE_CREDENTIALS_PATH")

    gemini_model: str = Field(default="gemini-1.5-pro", alias="LECTEUR_GEMINI_MODEL")

    cors_origins: str | None = Field(
        default="http://localhost:3000",
        alias=AliasChoices("CORS_ORIGINS", "LECTEUR_CORS_ORIGINS"),
    )

    max_segment_tokens: int = Field(default=512, alias="LECTEUR_MAX_SEGMENT_TOKENS")
    max_retry_attempts: int = Field(default=3, alias="LECTEUR_MAX_RETRY_ATTEMPTS")

    @computed_field(return_type=list[str])
    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
