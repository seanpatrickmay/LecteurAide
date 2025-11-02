import logging
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.entities import Book, Question, QuestionOption, Scene, Sentence, Vocabulary
from app.services.gemini import GeminiService
from app.services.pdf import extract_pdf_text
from app.services.translation import TranslationService
from app.utils.chunking import SentenceChunk, chunk_sentence_pairs
from app.utils.text import HeadingInfo, split_sentences, strip_headings


@dataclass
class IngestionResult:
    book: Book
    scene_count: int


@dataclass(slots=True)
class SentenceSlice:
    text: str
    start: int
    end: int
    paragraph_index: int


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
        self._logger = logging.getLogger(__name__)

    def ingest(
        self,
        title: str,
        pdf_bytes: bytes,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> IngestionResult:
        book_text = extract_pdf_text(pdf_bytes)
        book_text, stripped_headings = strip_headings(book_text)
        if stripped_headings:
            self._logger.debug(
                "Removed %d potential headings for book '%s': %s",
                len(stripped_headings),
                title,
                [heading.text for heading in stripped_headings],
            )
        settings = get_settings()

        def build_sentence_slices(source_text: str) -> list[SentenceSlice]:
            if not source_text.strip():
                return []

            lines = source_text.splitlines(True)
            paragraphs: list[tuple[str, int]] = []
            current_lines: list[str] = []
            paragraph_start: int | None = None
            position = 0

            for line in lines:
                if line.strip():
                    if paragraph_start is None:
                        paragraph_start = position
                    current_lines.append(line)
                else:
                    if current_lines and paragraph_start is not None:
                        paragraphs.append(("".join(current_lines), paragraph_start))
                        current_lines = []
                        paragraph_start = None
                position += len(line)

            if current_lines and paragraph_start is not None:
                paragraphs.append(("".join(current_lines), paragraph_start))

            if not paragraphs:
                paragraphs.append((source_text, 0))

            slices: list[SentenceSlice] = []
            max_chars = settings.max_prompt_chars
            search_start = 0

            for paragraph_index, (paragraph_text, paragraph_start) in enumerate(paragraphs):
                sentences = split_sentences(paragraph_text)
                if not sentences:
                    continue
                search_start = max(search_start, paragraph_start)
                for sentence in sentences:
                    if not sentence:
                        continue
                    idx = source_text.find(sentence, search_start)
                    if idx == -1:
                        idx = source_text.find(sentence)
                        if idx == -1:
                            continue
                    end_idx = idx + len(sentence)
                    if len(sentence) <= max_chars:
                        slices.append(
                            SentenceSlice(
                                text=sentence,
                                start=idx,
                                end=end_idx,
                                paragraph_index=paragraph_index,
                            )
                        )
                        search_start = end_idx
                        continue

                    segment_start = idx
                    while segment_start < end_idx:
                        segment_end = min(segment_start + max_chars, end_idx)
                        if segment_end < end_idx:
                            backtrack = source_text.rfind(" ", segment_start, segment_end)
                            if backtrack == -1 or backtrack <= segment_start + max_chars * 0.3:
                                backtrack = source_text.rfind("\n", segment_start, segment_end)
                            if backtrack != -1 and backtrack > segment_start:
                                segment_end = backtrack
                        segment_text = source_text[segment_start:segment_end].strip()
                        if segment_text:
                            slices.append(
                                SentenceSlice(
                                    text=segment_text,
                                    start=segment_start,
                                    end=segment_end,
                                    paragraph_index=paragraph_index,
                                )
                            )
                        if segment_end <= segment_start:
                            segment_end = min(segment_start + max_chars, end_idx)
                            if segment_end <= segment_start:
                                break
                        segment_start = segment_end
                    search_start = end_idx

            if slices:
                return slices

            stripped = source_text.strip()
            idx = source_text.find(stripped)
            if idx == -1:
                idx = 0
            return [SentenceSlice(text=stripped, start=idx, end=idx + len(stripped), paragraph_index=0)]

        def translate_in_batches(sentences: list[str]) -> list[str]:
            if not sentences:
                return []
            max_chars = settings.max_prompt_chars
            max_items = max(settings.max_translation_sentences, 1)
            results: list[str] = []
            batch: list[str] = []
            char_count = 0

            for sentence in sentences:
                text = sentence or ""
                length = max(len(text), 1)
                if batch and (char_count + length > max_chars or len(batch) >= max_items):
                    translated = list(self._translator.translate_sentences(batch))
                    if len(translated) < len(batch):
                        translated.extend([""] * (len(batch) - len(translated)))
                    results.extend(translated[: len(batch)])
                    batch.clear()
                    char_count = 0

                batch.append(text)
                char_count += length

            if batch:
                translated = list(self._translator.translate_sentences(batch))
                if len(translated) < len(batch):
                    translated.extend([""] * (len(batch) - len(translated)))
                results.extend(translated[: len(batch)])

            if len(results) < len(sentences):
                results.extend([""] * (len(sentences) - len(results)))
            return results[: len(sentences)]

        sentence_slices = build_sentence_slices(book_text)
        french_sentences = [slice_.text for slice_ in sentence_slices]

        english_sentences = translate_in_batches(french_sentences)

        heading_sentence_map: list[tuple[int, str]] = []
        if stripped_headings and sentence_slices:
            for heading in stripped_headings:
                heading_text = heading.text.strip()
                if not heading_text:
                    continue
                sentence_idx = 0
                while (
                    sentence_idx < len(sentence_slices)
                    and sentence_slices[sentence_idx].start < heading.char_index
                ):
                    sentence_idx += 1
                if sentence_idx >= len(sentence_slices):
                    sentence_idx = len(sentence_slices) - 1
                heading_sentence_map.append((max(sentence_idx, 0), heading_text))

            heading_sentence_map.sort(key=lambda item: item[0])

        def resolve_heading(sentence_index: int) -> str | None:
            heading_text: str | None = None
            for idx, text_value in heading_sentence_map:
                if idx <= sentence_index:
                    heading_text = text_value
                else:
                    break
            return heading_text

        def format_heading_text(raw: str | None) -> str | None:
            if not raw:
                return None
            stripped = raw.strip()
            if not stripped:
                return None
            if stripped.isupper():
                words = []
                for word in stripped.split():
                    if len(word) <= 3 and word.isupper():
                        words.append(word)
                    else:
                        words.append(word.capitalize())
                return " ".join(words)
            return stripped

        def generate_scene_title(
            existing_title: str | None,
            heading_text: str | None,
            default_sentence: str,
            scene_index: int,
        ) -> str:
            base = (existing_title or "").strip()
            if base.lower().startswith("scene"):
                base = ""

            formatted_heading = format_heading_text(heading_text)
            if formatted_heading:
                if base and formatted_heading.lower() not in base.lower():
                    return f"{formatted_heading}: {base}"
                if not base:
                    return formatted_heading
                return base

            if base:
                return base

            cleaned = default_sentence.strip().strip(".;:!?")
            if not cleaned:
                return f"Scene {scene_index}"
            snippet = " ".join(cleaned.split()[:8]).strip()
            if not snippet:
                return f"Scene {scene_index}"
            return snippet[0].upper() + snippet[1:]

        def build_prompt_segments(
            slices: list[SentenceSlice],
            translations: list[str],
            max_chars: int,
        ) -> list[tuple[str, list[str]]]:
            if not slices:
                return []

            segments: list[tuple[str, list[str]]] = []
            current_fr: list[str] = []
            current_en: list[str] = []
            current_chars = 0

            for slice_obj, translation in zip(slices, translations):
                segment_chars = len(slice_obj.text)
                translation_text = translation or ""
                if translation_text:
                    allowed_translation = max_chars - segment_chars - 1
                    if allowed_translation <= 0:
                        translation_text = ""
                    elif len(translation_text) > allowed_translation:
                        cutoff = translation_text.rfind(" ", 0, allowed_translation)
                        if cutoff == -1 or cutoff < allowed_translation * 0.3:
                            cutoff = allowed_translation
                        translation_text = translation_text[:cutoff].strip()
                    if translation_text:
                        segment_chars += len(translation_text) + 1
                segment_chars = max(segment_chars, 1)

                if current_fr and current_chars + segment_chars > max_chars:
                    segments.append(("\n".join(current_fr), current_en.copy()))
                    current_fr.clear()
                    current_en.clear()
                    current_chars = 0

                current_fr.append(slice_obj.text)
                current_en.append(translation_text)
                current_chars += segment_chars

            if current_fr:
                segments.append(("\n".join(current_fr), current_en.copy()))

            return segments

        chunks: list[SentenceChunk] = chunk_sentence_pairs(
            french_sentences,
            english_sentences,
            settings.max_segment_tokens,
            max_chunk_chars=settings.max_prompt_chars,
        )
        if not chunks and french_sentences:
            total_chars = sum(len(en) if en else len(fr) for en, fr in zip(english_sentences, french_sentences))
            chunks = [
                SentenceChunk(
                    index=0,
                    sentence_start=0,
                    sentence_end=len(french_sentences),
                    english_sentences=english_sentences,
                    french_sentences=french_sentences,
                    char_count=total_chars,
                )
            ]

        raw_scenes: list[dict[str, object]] = []

        if progress_callback:
            progress_callback(0, len(chunks))

        last_scene_summary: str | None = None

        last_scene_end_idx = -1

        for chunk in chunks:
            english_length = sum(len(sentence) for sentence in chunk.english_sentences)
            french_length = sum(len(sentence) for sentence in chunk.french_sentences)
            total_length = english_length + french_length
            self._logger.info(
                "Segment chunk %d/%d: english_chars=%d french_chars=%d total_chars=%d cap=%d",
                chunk.index + 1,
                len(chunks),
                english_length,
                french_length,
                total_length,
                settings.max_prompt_chars,
            )
            print(
                f"[Gemini Debug] segment_chunk {chunk.index + 1}/{len(chunks)} total_chars={total_length} cap={settings.max_prompt_chars}",
                flush=True,
            )
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

                start_paragraph = sentence_slices[global_start].paragraph_index
                while (
                    global_start > 0
                    and sentence_slices[global_start - 1].paragraph_index == start_paragraph
                ):
                    global_start -= 1

                end_paragraph = sentence_slices[global_end].paragraph_index
                while (
                    global_end + 1 < len(sentence_slices)
                    and sentence_slices[global_end + 1].paragraph_index == end_paragraph
                ):
                    global_end += 1

                if global_start <= last_scene_end_idx:
                    global_start = last_scene_end_idx + 1
                    if global_start > global_end:
                        continue
                    start_paragraph = sentence_slices[global_start].paragraph_index

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
                last_scene_end_idx = max(last_scene_end_idx, global_end)
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

            effective_cap = max(settings.max_prompt_chars, 1)
            prompt_segments = build_prompt_segments(sentence_slice, translations, effective_cap)
            if not prompt_segments:
                prompt_segments = [(content, list(translations))]
            else:
                combined_len = lambda item: len(item[0]) + len(" ".join(filter(None, item[1])))
                safety_floor = max(128, effective_cap // 8)
                while any(combined_len(segment) > settings.max_prompt_chars for segment in prompt_segments) and effective_cap > safety_floor:
                    effective_cap = max(effective_cap // 2, safety_floor)
                    prompt_segments = build_prompt_segments(sentence_slice, translations, effective_cap)
                    if not prompt_segments:
                        prompt_segments = [(content, list(translations))]
                        break

            for idx, (segment_text, segment_translations) in enumerate(prompt_segments, start=1):
                segment_length = len(segment_text) + len(" ".join(filter(None, segment_translations)))
                self._logger.info(
                    "Scene %d prompt segment %d/%d length=%d cap=%d",
                    index,
                    idx,
                    len(prompt_segments),
                    segment_length,
                    settings.max_prompt_chars,
                )
                print(
                    f"[Gemini Debug] scene {index} prompt segment {idx}/{len(prompt_segments)} length={segment_length} cap={settings.max_prompt_chars}",
                    flush=True,
                )

            heading_text = resolve_heading(scene_start)
            primary_sentence = sentences[0] if sentences else content.splitlines()[0] if content else ""
            scene_title = generate_scene_title(scene_data.get("title"), heading_text, primary_sentence, index)
            scene_data["title"] = scene_title

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

            seen_terms: set[str] = set()
            vocab_items: list[dict[str, str]] = []
            for segment_text, segment_translations in prompt_segments:
                prompt_length = len(segment_text) + len(" ".join(filter(None, segment_translations)))
                self._logger.info(
                    "Scene %d vocabulary prompt length=%d cap=%d",
                    index,
                    prompt_length,
                    settings.max_prompt_chars,
                )
                print(
                    f"[Gemini Debug] scene {index} vocabulary prompt length={prompt_length} cap={settings.max_prompt_chars}",
                    flush=True,
                )
                vocab_payload = self._gemini.extract_vocabulary(segment_text, segment_translations)
                for item in vocab_payload:
                    term = (item.get("term") or "").strip()
                    if not term:
                        continue
                    lower_term = term.lower()
                    if lower_term in seen_terms:
                        continue
                    seen_terms.add(lower_term)
                    vocab_items.append(item)

            for item in vocab_items:
                vocab = Vocabulary(
                    scene=scene,
                    term=item.get("term", ""),
                    part_of_speech=item.get("part_of_speech"),
                    definition=item.get("definition"),
                    example_sentence=item.get("example_sentence"),
                )
                if vocab.term:
                    self._session.add(vocab)

            aggregated_questions: list[dict[str, object]] = []
            for segment_text, _ in prompt_segments:
                if len(aggregated_questions) >= 4:
                    break
                prompt_length = len(segment_text)
                self._logger.info(
                    "Scene %d question prompt length=%d cap=%d",
                    index,
                    prompt_length,
                    settings.max_prompt_chars,
                )
                print(
                    f"[Gemini Debug] scene {index} question prompt length={prompt_length} cap={settings.max_prompt_chars}",
                    flush=True,
                )
                question_payload = self._gemini.generate_questions(segment_text)
                for question_data in question_payload:
                    aggregated_questions.append(question_data)
                    if len(aggregated_questions) >= 4:
                        break

            for question_data in aggregated_questions[:4]:
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
