from __future__ import annotations

from typing import Optional

from aiogram.types import InlineKeyboardMarkup, Message


def _has_media(message: Message) -> bool:
    return bool(message.photo or message.video or message.animation or message.document)


async def edit_text_or_caption(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    if _has_media(message):
        await message.edit_caption(caption=text, reply_markup=reply_markup)
    else:
        await message.edit_text(text, reply_markup=reply_markup)


