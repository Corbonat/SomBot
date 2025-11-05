from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.utils.texts import get_text


def build_main_menu(locale: str = "ru") -> InlineKeyboardMarkup:
    menu = get_text("menu.main", locale)
    builder = InlineKeyboardBuilder()
    builder.button(text=menu["about"], callback_data="info:about")
    builder.button(text=menu["rates"], callback_data="rates")
    builder.button(text=menu["education"], callback_data="education")
    builder.button(text=menu["hacker"], callback_data="hacker")
    builder.button(text=menu["guides"], callback_data="guides")
    builder.button(text=menu["aml"], callback_data="aml")
    builder.button(text=menu["lead"], callback_data="lead")
    builder.adjust(2, 2, 2)
    return builder.as_markup()
