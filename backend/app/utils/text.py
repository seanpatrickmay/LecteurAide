import re
from dataclasses import dataclass

_SENTENCE_REGEX = re.compile(r"(?<=[\.\?\!])\s+")
_HEADING_PATTERNS = [
    re.compile(r"^chapter\s+\w+$", re.IGNORECASE),
    re.compile(r"^part\s+\w+$", re.IGNORECASE),
    re.compile(r"^\d+$"),
    re.compile(r"^[ivxlcdm]+$", re.IGNORECASE),
]


@dataclass(slots=True)
class HeadingInfo:
    text: str
    char_index: int


def split_sentences(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    parts = _SENTENCE_REGEX.split(stripped)
    return [part.strip() for part in parts if part.strip()]


def strip_headings(text: str) -> tuple[str, list[HeadingInfo]]:
    """
    Remove obvious chapter/section headings while preserving body text.

    A heading is stripped only when it:
      * Exists on its own line (surrounded by blank lines or file boundaries), and
      * Matches common heading patterns (Chapter/Part labels, pure numerals, pure roman numerals),
        or is short and fully uppercase alphabetic text.
    """
    if not text:
        return text, []

    lines = text.splitlines()
    removed: list[HeadingInfo] = []
    cleaned_lines: list[str] = []
    total_lines = len(lines)
    output_offset = 0

    def _looks_like_heading(value: str) -> bool:
        stripped = value.strip()
        if not stripped:
            return False
        if len(stripped) > 80:
            return False
        for pattern in _HEADING_PATTERNS:
            if pattern.match(stripped):
                return True
        has_alpha = any(ch.isalpha() for ch in stripped)
        if has_alpha and stripped == stripped.upper():
            return True
        return False

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue

        prev_blank = index == 0 or not lines[index - 1].strip()
        next_blank = index == total_lines - 1 or not lines[index + 1].strip()

        if prev_blank and next_blank and _looks_like_heading(line):
            removed.append(HeadingInfo(text=stripped, char_index=output_offset))
            continue

        cleaned_lines.append(line)
        output_offset += len(line) + 1

    return "\n".join(cleaned_lines), removed
