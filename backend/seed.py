"""Seed demo data"""
from uuid import uuid4
from app.services.db.supabase_client import get_client


def main():
    supabase = get_client()
    book_id = str(uuid4())
    supabase.table("books").insert({
        "id": book_id,
        "title": "Demo Book",
        "author": "Anon",
        "language_code": "en",
        "description": "Demo description",
    }).execute()
    scene_id = str(uuid4())
    supabase.table("scenes").insert({
        "id": scene_id,
        "book_id": book_id,
        "scene_index": 1,
        "title": "Scene 1",
        "raw_text": "Hello world. Goodbye world.",
    }).execute()
    supabase.table("sentences").insert([
        {
            "id": str(uuid4()),
            "scene_id": scene_id,
            "sentence_index": 1,
            "source_text": "Hello world.",
            "translation_en": "Hello world.",
        },
        {
            "id": str(uuid4()),
            "scene_id": scene_id,
            "sentence_index": 2,
            "source_text": "Goodbye world.",
            "translation_en": "Goodbye world.",
        },
    ]).execute()
    print("Seed complete", book_id)


if __name__ == "__main__":
    main()
