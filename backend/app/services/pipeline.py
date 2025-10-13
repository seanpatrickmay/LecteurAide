from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.entities import Book, Question, QuestionOption, Scene, Sentence, Vocabulary
from app.services.gemini import GeminiService
from app.services.pdf import extract_pdf_text
from app.services.translation import TranslationService
from app.utils.chunking import SentenceChunk, chunk_sentence_pairs
from app.utils.text import split_sentences


@dataclass
class IngestionResult:
    book: Book
    scene_count: int


@dataclass(slots=True)
class SentenceSlice:
    text: str
    start: int
    end: int


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

        def build_sentence_slices(source_text: str) -> list[SentenceSlice]:
            raw_sentences = split_sentences(source_text)
            slices: list[SentenceSlice] = []
            search_start = 0

            for sentence in raw_sentences:
                if not sentence:
                    continue
                idx = source_text.find(sentence, search_start)
                if idx == -1:
                    idx = source_text.find(sentence)
                    if idx == -1:
                        continue
                end_idx = idx + len(sentence)
                slices.append(SentenceSlice(text=sentence, start=idx, end=end_idx))
                search_start = end_idx

            if slices:
                return slices

            stripped = source_text.strip()
            if not stripped:
                return []
            idx = source_text.find(stripped)
            if idx == -1:
                idx = 0
            return [SentenceSlice(text=stripped, start=idx, end=idx + len(stripped))]

        sentence_slices = build_sentence_slices(book_text)
        french_sentences = [slice_.text for slice_ in sentence_slices]

        english_sentences = (
            self._translator.translate_sentences(french_sentences) if french_sentences else []
        )
        if len(english_sentences) < len(french_sentences):
            english_sentences = list(english_sentences) + [""] * (
                len(french_sentences) - len(english_sentences)
            )

        chunks: list[SentenceChunk] = chunk_sentence_pairs(
            french_sentences,
            english_sentences,
            settings.max_segment_tokens,
        )
        if not chunks and french_sentences:
            chunks = [
                SentenceChunk(
                    index=0,
                    sentence_start=0,
                    sentence_end=len(french_sentences),
                    english_sentences=english_sentences,
                    french_sentences=french_sentences,
                )
            ]

        raw_scenes: list[dict[str, object]] = []

        if progress_callback:
            progress_callback(0, len(chunks))

        last_scene_summary: str | None = None

        for chunk in chunks:
            chunk_scenes = self._gemini.segment_chunk(
                chunk.english_sentences,
                chunk.french_sentences,
                chunk.index,
                len(chunks),
                previous_scene_summary=last_scene_summary,
            )
            sentence_count = len(chunk.english_sentences)
            for scene_data in chunk_scenes:
                raw_start = scene_data.get("start_sentence_index")
                raw_end = scene_data.get("end_sentence_index")

                def parse_index(value: object) -> int | None:
                    if isinstance(value, int):
                        return value
                    if isinstance(value, str) and value.strip():
                        try:
                            return int(value.strip())
                        except ValueError:
                            return None
                    return None

                start_index = parse_index(raw_start)
                end_index = parse_index(raw_end)
                if start_index is None or end_index is None:
                    continue
                start_offset = start_index - 1
                end_offset = end_index - 1
                if (
                    start_offset < 0
                    or end_offset < start_offset
                    or end_offset >= sentence_count
                ):
                    continue
                global_start = chunk.sentence_start + start_offset
                global_end = chunk.sentence_start + end_offset
                if global_start < 0 or global_end >= len(sentence_slices):
                    continue

                content_start = sentence_slices[global_start].start
                content_end = sentence_slices[global_end].end
                content_segment = book_text[content_start:content_end].strip()
                if not content_segment:
                    continue

                raw_scenes.append(
                    {
                        "title": scene_data.get("title"),
                        "summary": scene_data.get("summary"),
                        "content": content_segment,
                        "sentence_start": global_start,
                        "sentence_end": global_end,
                        "continues_from_previous": bool(scene_data.get("continues_from_previous")),
                        "continues_to_next": bool(scene_data.get("continues_to_next")),
                    }
                )
                summary_value = scene_data.get("summary")
                if isinstance(summary_value, str) and summary_value.strip():
                    last_scene_summary = summary_value.strip()
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
            scene_start = scene_data.get("sentence_start")
            scene_end = scene_data.get("sentence_end")
            if not isinstance(scene_start, int) or not isinstance(scene_end, int):
                continue

            if merged_scenes and continues_prev:
                last_scene = merged_scenes[-1]
                last_content = last_scene.get("content", "")
                last_start = last_scene.get("sentence_start")
                last_end = last_scene.get("sentence_end")
                if not isinstance(last_start, int) or not isinstance(last_end, int):
                    continue
                if isinstance(last_content, str):
                    combined_start = min(last_start, scene_start)
                    combined_end = max(last_end, scene_end)
                    start_char = sentence_slices[combined_start].start
                    end_char = sentence_slices[combined_end].end
                    combined = book_text[start_char:end_char].strip()
                    last_scene["content"] = combined
                    last_normalized = last_scene.get("_normalized", "")
                    if isinstance(last_normalized, str) and last_normalized in seen_normalized:
                        seen_normalized.discard(last_normalized)
                    new_normalized = normalize(combined)
                    last_scene["_normalized"] = new_normalized
                    last_scene["sentence_start"] = combined_start
                    last_scene["sentence_end"] = combined_end
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
                    "sentence_start": scene_start,
                    "sentence_end": scene_end,
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
            scene_start = scene_data.get("sentence_start")
            scene_end = scene_data.get("sentence_end")
            if not isinstance(scene_start, int) or not isinstance(scene_end, int):
                continue
            sentence_slice = sentence_slices[scene_start : scene_end + 1]
            sentences = [slice_.text for slice_ in sentence_slice]
            translations = english_sentences[scene_start : scene_end + 1]
            if len(translations) < len(sentences):
                translations = translations + [""] * (len(sentences) - len(translations))

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
