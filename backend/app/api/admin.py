from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from ..services.db.supabase_client import get_client
from ..services.pipeline.ingest import ingest_book

router = APIRouter(tags=["admin"])


class BookIn(BaseModel):
    title: str
    author: str
    language_code: str
    pdf_url: str | None = None


@router.post("/books")
async def create_book(book: BookIn):
    supabase = get_client()
    data = book.dict(exclude_none=True)
    data["id"] = str(uuid4())
    supabase.table("books").insert(data).execute()
    return {"book_id": data["id"]}


@router.post("/books/{book_id}/upload-url")
async def get_upload_url(book_id: str):
    supabase = get_client()
    try:
        res = supabase.storage.from_("books").create_signed_upload_url(f"{book_id}.pdf")
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"url": res["signedUrl"], "path": res["path"]}


@router.post("/books/{book_id}/ingest")
async def ingest(book_id: str):
    task = ingest_book.delay(book_id)
    return {"job_id": task.id}


@router.get("/jobs/{job_id}")
async def job_status(job_id: str):
    task = ingest_book.AsyncResult(job_id)
    return {"status": task.status}
