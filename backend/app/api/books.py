from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..services.db.supabase_client import get_client

router = APIRouter(prefix="/books", tags=["books"])


class Book(BaseModel):
    id: str
    title: str
    author: str
    language_code: str
    description: str | None = None
    cover_url: str | None = None


@router.get("", response_model=list[Book])
async def list_books(page: int = 1, page_size: int = 20):
    supabase = get_client()
    start = (page - 1) * page_size
    end = start + page_size - 1
    res = supabase.table("books").select("*").range(start, end).execute()
    return res.data or []


class Sentence(BaseModel):
    i: int
    source: str
    translation: str | None = None


class ScenePayload(BaseModel):
    sentences: list[Sentence]
    vocab: list[dict] | None = None
    questions: list[dict] | None = None
    answers: list[dict] | None = None


@router.get("/{book_id}/scenes/{scene_index}", response_model=ScenePayload)
async def get_scene(book_id: str, scene_index: int):
    supabase = get_client()
    scene = (
        supabase.table("scenes")
        .select("id, raw_text")
        .eq("book_id", book_id)
        .eq("scene_index", scene_index)
        .single()
        .execute()
    )
    if not scene.data:
        raise HTTPException(status_code=404, detail="Scene not found")
    sentences = (
        supabase.table("sentences")
        .select("sentence_index, source_text, translation_en")
        .eq("scene_id", scene.data["id"])
        .order("sentence_index")
        .execute()
    )
    exercises = (
        supabase.table("scene_exercises")
        .select("vocab, questions, answers")
        .eq("scene_id", scene.data["id"])
        .maybe_single()
        .execute()
    )
    return {
        "sentences": [
            {"i": s["sentence_index"], "source": s["source_text"], "translation": s["translation_en"]}
            for s in sentences.data or []
        ],
        "vocab": exercises.data.get("vocab") if exercises.data else [],
        "questions": exercises.data.get("questions") if exercises.data else [],
        "answers": exercises.data.get("answers") if exercises.data else [],
    }
