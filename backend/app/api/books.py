import json
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas import (
    BookItem,
    BookSummary,
    QuestionItem,
    QuestionOptionItem,
    SceneItem,
    SentenceItem,
    VocabularyItem,
)
from app.db.session import get_session
from app.dependencies import pipeline
from app.models.entities import Book, Question, Scene
from app.services.pipeline import IngestionPipeline

router = APIRouter(prefix="/books", tags=["books"])


@router.get(
    "",
    response_model=list[BookSummary],
)
def list_books(
    db: Session = Depends(get_session),
):
    stmt = select(Book).order_by(Book.created_at.desc()).options(
        selectinload(Book.scenes),
    )
    results = db.execute(stmt).scalars().unique().all()
    return [
        BookSummary(
            id=book.id,
            title=book.title,
            created_at=book.created_at,
            scene_count=len(book.scenes),
        )
        for book in results
    ]


@router.post(
    "/upload",
    response_model=None,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_book(
    title: str = Form(...),
    file: UploadFile = File(...),
    ingest_pipeline: IngestionPipeline = Depends(pipeline),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF uploads are supported.")

    pdf_bytes = await file.read()

    def event_stream():
        queue: Queue[str | None] = Queue()

        def progress_callback(processed: int, total: int):
            payload = {
                "type": "progress",
                "processed_chunks": processed,
                "total_chunks": total,
            }
            queue.put(json.dumps(payload))

        def run_ingest():
            try:
                result = ingest_pipeline.ingest(title=title, pdf_bytes=pdf_bytes, progress_callback=progress_callback)
                payload = {
                    "type": "completed",
                    "book_id": result.book.id,
                    "scene_count": result.scene_count,
                }
                queue.put(json.dumps(payload))
            except Exception as exc:  # pragma: no cover
                queue.put(json.dumps({"type": "error", "message": str(exc)}))
            finally:
                queue.put(None)

        def producer():
            with ThreadPoolExecutor(max_workers=1) as executor:
                executor.submit(run_ingest)
                while True:
                    item = queue.get()
                    if item is None:
                        break
                    yield f"data: {item}\n\n"

        return producer()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get(
    "/{book_id}",
    response_model=BookItem,
)
def get_book(
    book_id: int,
    db: Session = Depends(get_session),
):
    stmt = select(Book).where(Book.id == book_id).options(
        selectinload(Book.scenes).options(
            selectinload(Scene.sentences),
            selectinload(Scene.vocabulary),
            selectinload(Scene.questions).options(
                selectinload(Question.options)
            ),
        )
    )
    result = db.execute(stmt).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found.")

    return _book_to_schema(result)


def _book_to_schema(book: Book) -> BookItem:
    scenes = []
    for scene in sorted(book.scenes, key=lambda s: s.index):
        sentences = [
            SentenceItem(
                id=sentence.id,
                index=sentence.index,
                original_text=sentence.original_text,
                translated_text=sentence.translated_text,
            )
            for sentence in sorted(scene.sentences, key=lambda s: s.index)
        ]
        vocab_items = [
            VocabularyItem(
                id=vocab.id,
                term=vocab.term,
                part_of_speech=vocab.part_of_speech,
                definition=vocab.definition,
                example_sentence=vocab.example_sentence,
            )
            for vocab in scene.vocabulary
        ]
        question_items = [
            QuestionItem(
                id=question.id,
                prompt=question.prompt,
                options=[
                    QuestionOptionItem(
                        id=option.id,
                        text=option.text,
                        is_correct=option.is_correct,
                    )
                    for option in question.options
                ],
            )
            for question in scene.questions
        ]
        scenes.append(
            SceneItem(
                id=scene.id,
                index=scene.index,
                title=scene.title,
                summary=scene.summary,
                original_text=scene.original_text,
                sentences=sentences,
                vocabulary=vocab_items,
                questions=question_items,
            )
        )
    return BookItem(
        id=book.id,
        title=book.title,
        original_language=book.original_language,
        created_at=book.created_at,
        scenes=scenes,
    )
