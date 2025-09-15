from abc import ABC, abstractmethod


class Translator(ABC):
    @abstractmethod
    async def translate_many(self, sentences: list[str], source_lang: str, target_lang: str = "en") -> list[str]:
        ...
