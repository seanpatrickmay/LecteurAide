try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None
from .providers import Translator


class AwsTranslate(Translator):
    def __init__(self):
        if boto3:
            self.client = boto3.client("translate", region_name="us-east-1")
        else:  # pragma: no cover
            self.client = None

    async def translate_many(self, sentences: list[str], source_lang: str, target_lang: str = "en") -> list[str]:
        # TODO: call batch translate; stub for now
        return [f"{s} (en)" for s in sentences]
