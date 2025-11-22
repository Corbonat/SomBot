from __future__ import annotations

from pathlib import Path

from aiogram import Bot
from aiogram.types import InputMediaPhoto, FSInputFile
from redis.asyncio import Redis


def _key(chat_id: int) -> str:
    return f"main_photo:{chat_id}"


async def store_main_photo_id(redis: Redis, chat_id: int, message_id: int) -> None:
    """Сохраняем id сообщения с основной картинкой для чата."""
    await redis.set(_key(chat_id), str(message_id))


async def set_main_photo(redis: Redis, bot: Bot, chat_id: int, image_path: str) -> None:
    """
    Меняем медиа в ранее отправленном сообщении с основной картинкой.
    Если id не найден или файла нет — тихо выходим.
    """
    try:
        raw = await redis.get(_key(chat_id))
        if not raw:
            return
        msg_id = int(raw)
    except Exception:
        return

    path = Path(image_path)
    if not path.exists():
        return

    media = InputMediaPhoto(media=FSInputFile(path.as_posix()))
    try:
        await bot.edit_message_media(chat_id=chat_id, message_id=msg_id, media=media)
    except Exception:
        # Если сообщение удалено/не редактируется — просто игнорируем
        return


