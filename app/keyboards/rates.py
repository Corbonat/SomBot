from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.common import nav_row
from app.utils.texts import get_text


def build_sources_menu(locale: str = "ru") -> InlineKeyboardMarkup:
    texts = get_text("rates.sources", locale)
    builder = InlineKeyboardBuilder()
    builder.button(text=texts["rapira"], callback_data="rates:rapira:show")
    builder.button(text=texts["bybit"], callback_data="rates:bybit:menu")
    builder.button(text=texts["grinex"], callback_data="rates:grinex:show")
    builder.adjust(1)
    builder.attach(nav_row(back_cb="nav:home", home_cb="nav:home"))
    return builder.as_markup()


def build_rate_actions(callback_prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data=f"{callback_prefix}:refresh")
    builder.adjust(1)
    builder.attach(nav_row(back_cb="rates", home_cb="nav:home"))
    return builder.as_markup()

