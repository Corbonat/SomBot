from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery

from app.keyboards.common import nav_row
from app.utils.texts import get_text


router = Router(name="fallback")


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    # Catch-all for any callback_data that didn't match other handlers
    await callback.message.edit_text(
        get_text("common.coming_soon"), reply_markup=nav_row().as_markup()
    )
    await callback.answer()



