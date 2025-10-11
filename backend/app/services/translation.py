import os
from typing import Sequence

from google.cloud import translate_v3 as translate

from app.config import get_settings


class TranslationService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.google_project_id:
            raise RuntimeError("Google Cloud project id is not configured.")
        if settings.google_credentials_path:
            os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", settings.google_credentials_path)
        self._client = translate.TranslationServiceClient()
        self._parent = f"projects/{settings.google_project_id}/locations/{settings.google_location}"

    def translate_sentences(
        self,
        sentences: Sequence[str],
        source_language: str = "fr",
        target_language: str = "en",
    ) -> list[str]:
        if not sentences:
            return []
        response = self._client.translate_text(
            contents=list(sentences),
            parent=self._parent,
            source_language_code=source_language,
            target_language_code=target_language,
        )
        return [translation.translated_text for translation in response.translations]
