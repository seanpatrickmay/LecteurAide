from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TextChunk:
    index: int
    start: int
    end: int
    text: str


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
