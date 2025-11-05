from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message, FSInputFile

from app.keyboards.main_menu import build_main_menu
from app.utils.texts import get_text

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = get_text("menu.start")
    photo = FSInputFile("2.jpg")

    if len(text) <= 1024:
        await message.answer_photo(photo, caption=text, reply_markup=build_main_menu())
    else:
        await message.answer_photo(photo)
        await message.answer(text, reply_markup=build_main_menu())


@router.callback_query(lambda c: c.data == "nav:home")
async def back_to_home(callback: CallbackQuery) -> None:
    await callback.message.edit_text(get_text("menu.start"), reply_markup=build_main_menu())
    await callback.answer()
