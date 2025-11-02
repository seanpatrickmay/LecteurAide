import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(ROOT_DIR))

from app.config import get_settings  # noqa: E402
from app.db.session import Base  # noqa: E402
from app.models.entities import Scene  # noqa: E402
from app.services.pipeline import IngestionPipeline  # noqa: E402
from app.utils.chunking import chunk_sentence_pairs  # noqa: E402


class FakeTranslator:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def translate_sentences(self, sentences):
        combined = len(" ".join(sentences))
        self.calls.append(combined)
        return list(sentences)


class FakeGeminiService:
    def __init__(self, max_chars: int) -> None:
        self.max_chars = max_chars
        self.segment_inputs: list[int] = []
        self.vocab_prompts: list[int] = []
        self.question_prompts: list[int] = []

    def segment_chunk(
        self,
        english_sentences,
        french_sentences,
        chunk_index,
        total_chunks,
        previous_scene_summary=None,
    ):
        prompt_length = sum(len(sentence) for sentence in english_sentences)
        self.segment_inputs.append(prompt_length)
        return [
            {
                "title": f"Chunk {chunk_index + 1}",
                "summary": "Combined summary",
                "start_sentence_index": 1,
                "end_sentence_index": len(english_sentences),
                "continues_from_previous": chunk_index > 0,
                "continues_to_next": chunk_index < total_chunks - 1,
            }
        ]

    def extract_vocabulary(self, scene_text: str, translated_sentences):
        combined = len(scene_text) + len(" ".join(translated_sentences))
        self.vocab_prompts.append(combined)
        return []

    def generate_questions(self, scene_text: str):
        self.question_prompts.append(len(scene_text))
        return []


class PromptLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_env = dict(os.environ)
        os.environ["LECTEUR_MAX_PROMPT_CHARS"] = "1000"
        os.environ["LECTEUR_MAX_SEGMENT_TOKENS"] = "50000"
        os.environ["LECTEUR_DATABASE_URL"] = "sqlite:///:memory:"
        get_settings.cache_clear()

        self.settings = get_settings()
        engine = create_engine(self.settings.database_url, future=True)
        Base.metadata.create_all(engine)
        self._Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._original_env)
        get_settings.cache_clear()

    def test_chunk_sentence_pairs_respects_char_cap(self) -> None:
        max_chars = 1000
        french = ["a" * 400 + "." for _ in range(10)]
        english = ["b" * 400 + "." for _ in range(10)]
        chunks = chunk_sentence_pairs(
            french,
            english,
            max_tokens=50000,
            max_chunk_chars=max_chars,
        )
        for chunk in chunks:
            measured = sum(
                len(en) if en else len(fr)
                for en, fr in zip(chunk.english_sentences, chunk.french_sentences)
            )
            self.assertLessEqual(measured, max_chars)

    def test_scene_prompts_are_split_below_cap(self) -> None:
        session: Session = self._Session()
        gemini = FakeGeminiService(self.settings.max_prompt_chars)
        translator = FakeTranslator()
        long_sentence = ("Ceci est une phrase très longue " * 60).strip()
        text = ". ".join(long_sentence for _ in range(80)) + "."

        with patch("app.services.pipeline.extract_pdf_text", return_value=text):
            pipeline = IngestionPipeline(session, gemini, translator)
            pipeline.ingest("Long Book", b"dummy")

        scenes = session.scalars(select(Scene)).all()
        self.assertTrue(scenes)
        max_scene_length = max(len(scene.original_text) for scene in scenes)
        self.assertGreater(max_scene_length, self.settings.max_prompt_chars)

        self.assertTrue(gemini.vocab_prompts)
        self.assertTrue(gemini.question_prompts)
        self.assertLessEqual(max(gemini.vocab_prompts), self.settings.max_prompt_chars)
        self.assertLessEqual(max(gemini.question_prompts), self.settings.max_prompt_chars)
        self.assertTrue(all(call <= self.settings.max_prompt_chars for call in translator.calls))
        session.close()

    def test_translation_batches_stay_within_cap(self) -> None:
        session: Session = self._Session()
        gemini = FakeGeminiService(self.settings.max_prompt_chars)
        translator = FakeTranslator()
        very_long_sentence = ("Phrase extrêmement longue " * 80).strip()
        text = ". ".join(very_long_sentence for _ in range(60)) + "."

        with patch("app.services.pipeline.extract_pdf_text", return_value=text):
            pipeline = IngestionPipeline(session, gemini, translator)
            pipeline.ingest("Another Book", b"dummy")

        self.assertTrue(translator.calls, "Translator should have been invoked")
        self.assertTrue(all(length <= self.settings.max_prompt_chars for length in translator.calls))
        session.close()


if __name__ == "__main__":
    unittest.main()
