import re

_SENTENCE_REGEX = re.compile(r"(?<=[\.\?\!])\s+")


def split_sentences(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    parts = _SENTENCE_REGEX.split(stripped)
    return [part.strip() for part in parts if part.strip()]
