from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.config import Settings
from pred.keyboards.cta import build_cta
from pred.services.phrases import PhraseService

router = Router(name="pred-predict")


@router.message(Command("predict"))
async def handle_predict(message: Message, phrase_service: PhraseService, settings: Settings) -> None:
    phrase = await phrase_service.get_random_phrase()
    url = settings.academy_url or "https://t.me/"
    await message.answer(phrase.text, reply_markup=build_cta(url))
