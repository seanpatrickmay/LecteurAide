from fastapi import APIRouter, Header
from pydantic import BaseModel
from ..services.db.supabase_client import get_client

router = APIRouter(tags=["progress"])


class ProgressIn(BaseModel):
    book_id: str
    scene_index: int


@router.post("/progress")
async def post_progress(payload: ProgressIn, x_user_id: str = Header(...)):
    supabase = get_client()
    supabase.table("user_progress").upsert(
        {
            "user_id": x_user_id,
            "book_id": payload.book_id,
            "last_scene_index": payload.scene_index,
        },
        on_conflict="user_id,book_id",
    ).execute()
    return {"status": "ok"}
