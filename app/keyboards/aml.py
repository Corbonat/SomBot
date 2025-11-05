from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.common import nav_row
from app.utils.texts import get_text


def build_aml_menu(locale: str = "ru") -> InlineKeyboardMarkup:
    texts = get_text("aml.buttons", locale)
    builder = InlineKeyboardBuilder()
    builder.button(text=texts["check"], callback_data="aml:check:start")
    builder.button(text=texts["policy"], callback_data="aml:policy")
    builder.adjust(1)
    builder.attach(nav_row(back_cb="nav:home", home_cb="nav:home"))
    return builder.as_markup()


def build_aml_result() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💾 Сохранить отчёт", callback_data="aml:result:export")
    builder.button(text="🔁 Проверить другой", callback_data="aml:check:start")
    builder.adjust(1)
    builder.attach(nav_row())
    return builder.as_markup()
