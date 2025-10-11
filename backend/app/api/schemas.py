from datetime import datetime
from typing import Sequence

from pydantic import BaseModel


class VocabularyItem(BaseModel):
    id: int
    term: str
    part_of_speech: str | None = None
    definition: str | None = None
    example_sentence: str | None = None


class SentenceItem(BaseModel):
    id: int
    index: int
    original_text: str
    translated_text: str


class QuestionOptionItem(BaseModel):
    id: int
    text: str
    is_correct: bool


class QuestionItem(BaseModel):
    id: int
    prompt: str
    options: Sequence[QuestionOptionItem]


class SceneItem(BaseModel):
    id: int
    index: int
    title: str | None = None
    summary: str | None = None
    original_text: str
    sentences: Sequence[SentenceItem]
    vocabulary: Sequence[VocabularyItem]
    questions: Sequence[QuestionItem]


class BookItem(BaseModel):
    id: int
    title: str
    original_language: str
    created_at: datetime
    scenes: Sequence[SceneItem]


class BookSummary(BaseModel):
    id: int
    title: str
    created_at: datetime
    scene_count: int
