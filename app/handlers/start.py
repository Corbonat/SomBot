from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message, FSInputFile

from app.keyboards.main_menu import build_main_menu
from app.keyboards.common import build_persistent_start_keyboard
from app.utils.texts import get_text
from app.utils.telegram import edit_text_or_caption

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = get_text("menu.start")
    photo = FSInputFile("2.jpg")
    # Всегда отправляем фото отдельно БЕЗ клавиатуры, затем текст С клавиатурой.
    # Это гарантирует, что дальнейшие правки меню редактируют текст, а не подпись к фото.
    await message.answer_photo(photo, reply_markup=build_persistent_start_keyboard())
    await message.answer(text, reply_markup=build_main_menu())


@router.callback_query(lambda c: c.data == "nav:home")
async def back_to_home(callback: CallbackQuery) -> None:
    await edit_text_or_caption(callback.message, get_text("menu.start"), build_main_menu())
    await callback.answer()
