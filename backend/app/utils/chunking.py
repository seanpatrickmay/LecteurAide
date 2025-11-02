from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TextChunk:
    index: int
    start: int
    end: int
    text: str


@dataclass(slots=True)
class SentenceChunk:
    index: int
    sentence_start: int  # inclusive
    sentence_end: int  # exclusive
    english_sentences: list[str]
    french_sentences: list[str]
    char_count: int


def chunk_text(
    text: str,
    max_tokens: int,
    overlap_ratio: float = 0.1,
    min_chunk_tokens: int = 128,
) -> list[TextChunk]:
    """
    Split raw text into overlapping chunks sized for LLM prompts.

    Roughly translates token counts into character counts (4 chars per token),
    applying an overlap to reduce abrupt context loss between chunks.
    """
    cleaned = text.strip()
    if not cleaned:
        return []

    # Guard rails for chunk sizing.
    tokens_per_chunk = max(max_tokens, min_chunk_tokens)
    approx_chars = tokens_per_chunk * 4
    overlap_chars = int(approx_chars * overlap_ratio)

    chunks: list[TextChunk] = []
    length = len(cleaned)
    start = 0
    chunk_index = 0

    while start < length:
        end = min(start + approx_chars, length)

        # Avoid splitting mid-word if possible by backtracking to whitespace.
        if end < length:
            boundary = cleaned.rfind("\n", start, end)
            if boundary == -1:
                boundary = cleaned.rfind(" ", start, end)
            if boundary != -1 and boundary > start + 200:
                end = boundary

        chunk_text = cleaned[start:end].strip()
        if chunk_text:
            chunks.append(TextChunk(index=chunk_index, start=start, end=end, text=chunk_text))
            chunk_index += 1

        if end >= length:
            break

        start = max(end - overlap_chars, 0)

    return chunks


def chunk_sentence_pairs(
    french_sentences: list[str],
    english_sentences: list[str],
    max_tokens: int,
    overlap_ratio: float = 0.1,
    min_chunk_tokens: int = 128,
    max_chunk_chars: int | None = None,
) -> list[SentenceChunk]:
    """
    Group aligned French/English sentences into chunks sized for LLM prompts.

    Chunk sizing uses the translated (English) sentence lengths to approximate
    token counts, ensuring the model sees English text for segmentation while
    preserving the mapping back to the original French sentences.
    """
    if not french_sentences:
        return []

    tokens_per_chunk = max(max_tokens, min_chunk_tokens)
    approx_chars = tokens_per_chunk * 4

    total_sentences = len(french_sentences)
    # Ensure the English list covers all sentences to avoid index checks later.
    if len(english_sentences) < total_sentences:
        english_sentences = english_sentences + [""] * (total_sentences - len(english_sentences))

    if max_chunk_chars is None or max_chunk_chars <= 0:
        max_chunk_chars = approx_chars

    chunks: list[SentenceChunk] = []
    start = 0
    chunk_index = 0

    while start < total_sentences:
        end = start
        english_chunk: list[str] = []
        french_chunk: list[str] = []
        measured_chars = 0

        while end < total_sentences:
            fr_sentence = french_sentences[end]
            en_sentence = english_sentences[end]

            sentence_chars = len(en_sentence) if en_sentence else len(fr_sentence)
            sentence_chars = max(sentence_chars, 1)

            if measured_chars + sentence_chars > max_chunk_chars and english_chunk:
                break

            french_chunk.append(fr_sentence)
            english_chunk.append(en_sentence)
            measured_chars += sentence_chars
            end += 1

            if measured_chars >= approx_chars:
                break

        if not french_chunk:
            break

        chunks.append(
            SentenceChunk(
                index=chunk_index,
                sentence_start=start,
                sentence_end=end,
                english_sentences=english_chunk,
                french_sentences=french_chunk,
                char_count=measured_chars,
            )
        )
        chunk_index += 1

        if end >= total_sentences:
            break

        overlap_sentences = int((end - start) * overlap_ratio)
        next_start = max(end - overlap_sentences, start + 1)
        start = min(next_start, total_sentences)

    return chunks
