from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services.gemini import GeminiService
from app.services.pipeline import IngestionPipeline
from app.services.translation import TranslationService


@lru_cache
def _gemini_service() -> GeminiService:
    return GeminiService()


@lru_cache
def _translation_service() -> TranslationService:
    return TranslationService()


def gemini_service() -> GeminiService:
    return _gemini_service()


def translation_service() -> TranslationService:
    return _translation_service()


def pipeline(
    db: Session = Depends(get_session),
) -> IngestionPipeline:
    return IngestionPipeline(db, gemini_service(), translation_service())
