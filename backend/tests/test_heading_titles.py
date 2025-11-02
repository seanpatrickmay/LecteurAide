import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("LECTEUR_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("LECTEUR_MAX_PROMPT_CHARS", "4000")
os.environ.setdefault("LECTEUR_MAX_SEGMENT_TOKENS", "4000")

from app.config import get_settings  # noqa: E402
get_settings.cache_clear()
from app.db.session import Base  # noqa: E402
from app.models.entities import Scene  # noqa: E402
from app.services.pipeline import IngestionPipeline  # noqa: E402


class StubTranslator:
    def translate_sentences(self, sentences):
        return [sentence for sentence in sentences]


class TitleGemini:
    def segment_chunk(self, english, french, chunk_index, total_chunks, previous_scene_summary=None):
        if chunk_index == 0:
            return [
                {
                    "title": "",
                    "summary": "",
                    "start_sentence_index": 1,
                    "end_sentence_index": 2,
                    "continues_from_previous": False,
                    "continues_to_next": False,
                },
                {
                    "title": "Un marché",
                    "summary": "",
                    "start_sentence_index": 3,
                    "end_sentence_index": len(english),
                    "continues_from_previous": False,
                    "continues_to_next": False,
                },
            ]
        return []

    def extract_vocabulary(self, scene_text, translated_sentences):
        return []

    def generate_questions(self, scene_text):
        return []


class HeadingTitleTests(unittest.TestCase):
    def setUp(self) -> None:
        get_settings.cache_clear()
        settings = get_settings()
        engine = create_engine(settings.database_url)
        Base.metadata.create_all(engine)
        self._engine = engine
        self.Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self._engine)
        get_settings.cache_clear()

    def test_headings_influence_scene_titles(self) -> None:
        session: Session = self.Session()
        pipeline = IngestionPipeline(session, TitleGemini(), StubTranslator())
        text = (
            "CHAPTER I\n\n"
            "Il était une fois. Une introduction calme.\n\n"
            "PART II\n\n"
            "La scène du marché commence ici. Les clients arrivent."
        )
        with patch("app.services.pipeline.extract_pdf_text", return_value=text):
            pipeline.ingest("Conte", b"pdf")

        scenes = session.scalars(select(Scene).order_by(Scene.index)).all()
        self.assertEqual(len(scenes), 2)
        self.assertEqual(scenes[0].title, "Chapter I")
        self.assertEqual(scenes[1].title, "Part II: Un marché")
        session.close()


class ParagraphBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        get_settings.cache_clear()
        settings = get_settings()
        engine = create_engine(settings.database_url)
        Base.metadata.create_all(engine)
        self._engine = engine
        self.Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self._engine)
        get_settings.cache_clear()

    def test_scene_does_not_split_paragraph(self) -> None:
        session: Session = self.Session()

        class BoundaryGemini:
            def segment_chunk(self, english, french, chunk_index, total_chunks, previous_scene_summary=None):
                return [
                    {
                        "title": "",
                        "summary": "",
                        "start_sentence_index": 1,
                        "end_sentence_index": 1,
                        "continues_from_previous": False,
                        "continues_to_next": False,
                    },
                    {
                        "title": "",
                        "summary": "",
                        "start_sentence_index": 2,
                        "end_sentence_index": len(english),
                        "continues_from_previous": False,
                        "continues_to_next": False,
                    },
                ]

            def extract_vocabulary(self, scene_text, translations):
                return []

            def generate_questions(self, scene_text):
                return []

        text = (
            "Paragraph one sentence one. Paragraph one sentence two.\n\n"
            "Paragraph two sentence one. Paragraph two sentence two."
        )
        pipeline = IngestionPipeline(session, BoundaryGemini(), StubTranslator())
        with patch("app.services.pipeline.extract_pdf_text", return_value=text):
            pipeline.ingest("Boundary Test", b"pdf")

        scenes = session.scalars(select(Scene).order_by(Scene.index)).all()
        self.assertEqual(len(scenes), 2)
        first_scene_sentences = [sentence.original_text for sentence in scenes[0].sentences]
        second_scene_sentences = [sentence.original_text for sentence in scenes[1].sentences]

        self.assertEqual(first_scene_sentences, ["Paragraph one sentence one.", "Paragraph one sentence two."])
        self.assertEqual(
            second_scene_sentences,
            ["Paragraph two sentence one.", "Paragraph two sentence two."],
        )
        session.close()


if __name__ == "__main__":
    unittest.main()
