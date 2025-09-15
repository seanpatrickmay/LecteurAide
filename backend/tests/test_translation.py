import asyncio
from app.services.translation.aws_translate import AwsTranslate


async def _run():
    tr = AwsTranslate()
    res = await tr.translate_many(["hola"], "es")
    assert res[0].endswith("(en)")


def test_translate_many():
    asyncio.run(_run())
