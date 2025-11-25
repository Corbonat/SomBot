from __future__ import annotations

from typing import Optional

from aiogram.types import (
    ForceReply,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

DEFAULT_PREVIEW_URL = "https://kbqvhfqs58zvukxe.public.blob.vercel-storage.com/IMG_20251121_190351_537.jpg"
_INVISIBLE_CHAR = "\u200b"

ReplyMarkupType = (
    InlineKeyboardMarkup
    | ReplyKeyboardMarkup
    | ReplyKeyboardRemove
    | ForceReply
    | None
)


def format_with_preview(
    text: str,
    preview_url: Optional[str] = None,
    with_preview: bool = True,
) -> str:
    if not with_preview:
        return text
    url = preview_url or DEFAULT_PREVIEW_URL
    return f'<a href="{url}">{_INVISIBLE_CHAR}</a>\n\n{text}'


async def answer_with_preview(
    message: Message,
    text: str,
    reply_markup: ReplyMarkupType = None,
    preview_url: Optional[str] = None,
    with_preview: bool = True,
):
    final_text = format_with_preview(text, preview_url, with_preview)
    return await message.answer(final_text, reply_markup=reply_markup)


def _has_media(message: Message) -> bool:
    return bool(message.photo or message.video or message.animation or message.document)


async def edit_text_or_caption(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    preview_url: Optional[str] = None,
    with_preview: bool = True,
    replace_media: bool = False,
) -> None:
    has_media = _has_media(message)
    if has_media and replace_media:
        await message.delete()
        await answer_with_preview(
            message,
            text,
            reply_markup=reply_markup,
            preview_url=preview_url,
            with_preview=with_preview,
        )
        return

    final_text = format_with_preview(text, preview_url, with_preview and not has_media)
    if has_media:
        await message.edit_caption(caption=final_text, reply_markup=reply_markup)
    else:
        await message.edit_text(final_text, reply_markup=reply_markup)

