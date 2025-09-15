from openai import AsyncOpenAI
from ..config import get_settings

settings = get_settings()
client = AsyncOpenAI(api_key=settings.openai_api_key)


async def generate_vocab(scene_text: str) -> list[dict]:
    # TODO: implement JSON-mode prompt
    return []


async def generate_questions(scene_text: str) -> dict:
    # TODO: implement JSON-mode prompt for questions/answers
    return {"questions": [], "answers": []}
