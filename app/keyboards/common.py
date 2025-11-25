from __future__ import annotations

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def nav_row(back_cb: str = "nav:back", home_cb: str = "nav:home") -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data=back_cb)
    builder.button(text="🏠 В главное меню", callback_data=home_cb)
    builder.adjust(2)
    return builder


def single_back(callback: str = "nav:back") -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data=callback)
    return builder
