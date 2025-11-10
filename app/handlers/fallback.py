from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery

from app.keyboards.common import nav_row
from app.utils.texts import get_text
from app.utils.telegram import edit_text_or_caption


router = Router(name="fallback")


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    # Catch-all for any callback_data that didn't match other handlers
    await edit_text_or_caption(callback.message, get_text("common.coming_soon"), nav_row().as_markup())
    await callback.answer()



