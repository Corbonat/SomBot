from __future__ import annotations

import asyncio

import httpx
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.fsm.storage.redis import RedisStorage

from app.core.bot import create_bot, create_dispatcher, setup_dispatcher, shutdown_bot
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.core.redis import close_redis, create_redis
from pred.handlers import register_handlers
from pred.services.phrases import PhraseService


async def build_dispatcher(settings: Settings) -> Dispatcher:
    redis = create_redis(settings.redis_url)
    storage = RedisStorage(redis=redis)
    dp = create_dispatcher(storage=storage)
    setup_dispatcher(dp)

    http_client = httpx.AsyncClient(timeout=10.0)

    dp["settings"] = settings
    dp["redis"] = redis
    dp["http_client"] = http_client
    dp["phrase_service"] = PhraseService()

    register_handlers(dp)
    return dp


async def run() -> None:
    settings = get_settings()
    setup_logging()
    bot = create_bot(settings.pred_bot_token.get_secret_value())
    bot.default = DefaultBotProperties(parse_mode=ParseMode.HTML)


    dp = await build_dispatcher(settings)

    try:
        await dp.start_polling(bot)
    finally:
        await shutdown(dp, bot)


async def shutdown(dp: Dispatcher, bot: Bot) -> None:
    http_client: httpx.AsyncClient = dp["http_client"]
    redis = dp["redis"]

    await http_client.aclose()
    await dp.storage.close()
    wait_closed = getattr(dp.storage, "wait_closed", None)
    if callable(wait_closed):
        await wait_closed()
    await close_redis(redis)
    await shutdown_bot(bot)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
