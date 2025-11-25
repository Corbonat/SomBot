from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.core.config import Settings
from pred.keyboards.cta import build_cta


router = Router(name="pred-start")


@router.message(CommandStart())
async def cmd_start(message: Message, settings: Settings) -> None:
    text = (
        "Привет! Это предсказ-бот VARSHER.\n\n"
        "Команды:\n"
        "— /predict — получить предсказание"
    )
    url = settings.academy_url or "https://t.me/"
    await message.answer(text, reply_markup=build_cta(url))


