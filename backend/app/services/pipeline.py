from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.entities import Book, Question, QuestionOption, Scene, Sentence, Vocabulary
from app.services.gemini import GeminiService
from app.services.pdf import extract_pdf_text
from app.services.translation import TranslationService
from app.utils.chunking import TextChunk, chunk_text
from app.utils.text import split_sentences


@dataclass
class IngestionResult:
    book: Book
    scene_count: int


class IngestionPipeline:
    def __init__(
        self,
        session: Session,
        gemini_service: GeminiService,
        translation_service: TranslationService,
    ) -> None:
        self._session = session
        self._gemini = gemini_service
        self._translator = translation_service

    def ingest(
        self,
        title: str,
        pdf_bytes: bytes,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> IngestionResult:
        book_text = extract_pdf_text(pdf_bytes)
        settings = get_settings()
        chunks = chunk_text(book_text, settings.max_segment_tokens)
        if not chunks:
            chunks = [TextChunk(index=0, start=0, end=len(book_text), text=book_text)]

        raw_scenes: list[dict[str, object]] = []

        if progress_callback:
            progress_callback(0, len(chunks))

        for chunk in chunks:
            chunk_scenes = self._gemini.segment_chunk(chunk.text, chunk.index, len(chunks))
            for scene_data in chunk_scenes:
                content = (scene_data.get("content") or "").strip()
                if not content:
                    continue
                raw_scenes.append(
                    {
                        "title": scene_data.get("title"),
                        "summary": scene_data.get("summary"),
                        "content": content,
                        "continues_from_previous": bool(scene_data.get("continues_from_previous")),
                        "continues_to_next": bool(scene_data.get("continues_to_next")),
                    }
                )
            if progress_callback:
                processed = min(chunk.index + 1, len(chunks))
                total = max(len(chunks), 1)
                progress_callback(processed, total)

        merged_scenes: list[dict[str, object]] = []
        seen_normalized: set[str] = set()

        def normalize(value: str) -> str:
            return " ".join(value.split())

        for scene_data in raw_scenes:
            content = scene_data["content"]  # type: ignore[index]
            if not isinstance(content, str):
                continue
            normalized = normalize(content)
            continues_prev = bool(scene_data.get("continues_from_previous"))

            if merged_scenes and continues_prev:
                last_scene = merged_scenes[-1]
                last_content = last_scene.get("content", "")
                if isinstance(last_content, str):
                    combined = f"{last_content}\n\n{content}".strip()
                    last_scene["content"] = combined
                    last_normalized = last_scene.get("_normalized", "")
                    if isinstance(last_normalized, str) and last_normalized in seen_normalized:
                        seen_normalized.discard(last_normalized)
                    new_normalized = normalize(combined)
                    last_scene["_normalized"] = new_normalized
                    seen_normalized.add(new_normalized)
                    last_summary = last_scene.get("summary")
                    new_summary = scene_data.get("summary")
                    if isinstance(new_summary, str) and new_summary.strip():
                        if isinstance(last_summary, str) and last_summary.strip():
                            last_scene["summary"] = f"{last_summary.strip()} {new_summary.strip()}"
                        else:
                            last_scene["summary"] = new_summary.strip()
                    continue

            if normalized in seen_normalized:
                continue

            seen_normalized.add(normalized)
            merged_scenes.append(
                {
                    "title": scene_data.get("title"),
                    "summary": scene_data.get("summary"),
                    "content": content,
                    "_normalized": normalized,
                }
            )

        book = Book(title=title, original_language="fr")
        self._session.add(book)
        created_scenes: list[Scene] = []

        for index, scene_data in enumerate(merged_scenes, start=1):
            scene_data.pop("_normalized", None)
            content = (scene_data.get("content") or "").strip()
            if not content:
                continue
            sentences = split_sentences(content)
            translations = self._translator.translate_sentences(sentences)
            if len(translations) != len(sentences):
                translations = list(translations) + [""] * (len(sentences) - len(translations))

            scene = Scene(
                book=book,
                index=index,
                title=scene_data.get("title"),
                summary=scene_data.get("summary"),
                original_text=content,
            )
            self._session.add(scene)
            self._session.flush()
            created_scenes.append(scene)

            for idx, (original, translated) in enumerate(zip(sentences, translations), start=1):
                sentence = Sentence(
                    scene=scene,
                    index=idx,
                    original_text=original,
                    translated_text=translated,
                )
                self._session.add(sentence)

            vocab_payload = self._gemini.extract_vocabulary(content, translations)
            for item in vocab_payload:
                vocab = Vocabulary(
                    scene=scene,
                    term=item.get("term", ""),
                    part_of_speech=item.get("part_of_speech"),
                    definition=item.get("definition"),
                    example_sentence=item.get("example_sentence"),
                )
                if vocab.term:
                    self._session.add(vocab)

            question_payload = self._gemini.generate_questions(content)
            for question_data in question_payload[:4]:
                prompt = (question_data.get("prompt") or "").strip()
                options_data = question_data.get("options") or []
                if not prompt or not isinstance(options_data, list):
                    continue

                parsed_options: list[tuple[str, bool]] = []
                for option_data in options_data:
                    text = (option_data.get("text") or "").strip()
                    raw_correct = option_data.get("is_correct")
                    if isinstance(raw_correct, bool):
                        is_correct = raw_correct
                    elif isinstance(raw_correct, str):
                        is_correct = raw_correct.strip().lower() in {"true", "yes", "1"}
                    else:
                        is_correct = False
                    if text:
                        parsed_options.append((text, is_correct))
                    if len(parsed_options) == 4:
                        break

                if len(parsed_options) != 4:
                    continue
                if sum(1 for _, flag in parsed_options if flag) != 1:
                    continue

                question = Question(scene=scene, prompt=prompt)
                self._session.add(question)
                self._session.flush()

                for text, is_correct in parsed_options:
                    option = QuestionOption(
                        question=question,
                        text=text,
                        is_correct=is_correct,
                    )
                    self._session.add(option)

        self._session.commit()
        self._session.refresh(book)
        return IngestionResult(book=book, scene_count=len(created_scenes))
