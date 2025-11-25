from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.keyboards.main_menu import build_main_menu
from app.utils.texts import get_text
from app.utils.telegram import answer_with_preview, edit_text_or_caption

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    # Одно основное сообщение: HTML‑ссылка на картинку (дефолтная) + главное меню
    await answer_with_preview(message, get_text("menu.start"), reply_markup=build_main_menu())


@router.callback_query(lambda c: c.data == "nav:home")
async def back_to_home(callback: CallbackQuery) -> None:
    # Возврат на тот же экран: превью + главное меню
    await edit_text_or_caption(
        callback.message,
        get_text("menu.start"),
        build_main_menu(),
        replace_media=True,
    )
    await callback.answer()
