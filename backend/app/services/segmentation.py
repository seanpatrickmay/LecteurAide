try:
    import nltk  # type: ignore
except Exception:  # pragma: no cover
    nltk = None


def split_into_scenes(text: str) -> list[str]:
    return [s.strip() for s in text.split("\n\n") if s.strip()]


def split_into_sentences(lang: str, scene_text: str) -> list[str]:
    if nltk:
        from nltk.tokenize import sent_tokenize
        try:
            return [s.strip() for s in sent_tokenize(scene_text, language=lang)]
        except LookupError:
            pass
    return [s.strip() for s in scene_text.split(".") if s.strip()]
