from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message, FSInputFile, URLInputFile
from pathlib import Path

from redis.asyncio import Redis

from app.keyboards.main_menu import build_main_menu
from app.keyboards.common import build_persistent_start_keyboard
from app.utils.main_photo import set_main_photo, store_main_photo_id
from app.utils.texts import get_text
from app.utils.telegram import edit_text_or_caption

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, redis: Redis) -> None:
    photo_path = Path("assets/images/main.jpg")
    base_text = get_text("menu.start")
    url = "https://kbqvhfqs58zvukxe.public.blob.vercel-storage.com/IMG_20251121_190351_537.jpg"

    # 1) Картинка как часть сообщения (превью по ссылке в тексте)
    inline_text = f'<a href="{url}">💳</a>\n\n{base_text}'
    await message.answer(inline_text)

    # 2) Фото по ссылке + caption с тем же текстом
    url_photo = URLInputFile(url)
    await message.answer_photo(url_photo, caption=inline_text)

    # 3) Картинка отдельно (основной экран) + клавиатура /start и сохранение main-photo id
    if photo_path.exists():
        photo = FSInputFile(photo_path.as_posix())
        sent = await message.answer_photo(photo, reply_markup=build_persistent_start_keyboard())
        await store_main_photo_id(redis, message.chat.id, sent.message_id)
    else:
        await message.answer("Картинка стартового экрана пока не загружена.", reply_markup=build_persistent_start_keyboard())

    # Главное меню (без дополнительной картинки)
    await message.answer(base_text, reply_markup=build_main_menu())


@router.callback_query(lambda c: c.data == "nav:home")
async def back_to_home(callback: CallbackQuery, redis: Redis) -> None:
    # При возврате домой возвращаем основную картинку
    await set_main_photo(redis, callback.message.bot, callback.message.chat.id, "assets/images/main.jpg")
    await edit_text_or_caption(callback.message, get_text("menu.start"), build_main_menu())
    await callback.answer()
