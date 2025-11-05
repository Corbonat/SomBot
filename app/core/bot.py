from __future__ import annotations

from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage


def create_bot(token: str) -> Bot:
    session = AiohttpSession()
    return Bot(token=token, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def create_dispatcher(storage: Optional[BaseStorage] = None) -> Dispatcher:
    return Dispatcher(storage=storage)


def setup_dispatcher(dp: Dispatcher) -> None:
    """Placeholder hook for middlewares/filters registration."""
    # Middlewares, filters, and other dispatcher-level configuration will live here.
    return None


async def shutdown_bot(bot: Bot) -> None:
    await bot.session.close()