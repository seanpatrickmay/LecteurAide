from celery import Celery
from ..config import get_settings

settings = get_settings()
celery_app = Celery("lecteuraide", broker=settings.redis_url)


@celery_app.task
def ingest_book(book_id: str):  # pragma: no cover - stub
    """Ingestion pipeline orchestrator"""
    # Steps: download pdf -> extract -> segment -> translate -> generate exercises -> persist
    return {"status": "completed", "book_id": book_id}
