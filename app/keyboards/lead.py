from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.common import nav_row
from app.utils.texts import get_text


def build_lead_menu(locale: str = "ru") -> InlineKeyboardMarkup:
    texts = get_text("lead.buttons", locale)
    builder = InlineKeyboardBuilder()
    builder.button(text=texts["contact"], url=get_text("links.contact"))
    builder.button(text=texts["form"], callback_data="lead:form:start")
    builder.adjust(1)
    builder.attach(nav_row(back_cb="nav:home", home_cb="nav:home"))
    return builder.as_markup()


def build_lead_question_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="lead:form:cancel")
    return builder.as_markup()


def build_lead_confirm() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data="lead:form:submit")
    builder.button(text="✏️ Исправить", callback_data="lead:form:restart")
    builder.button(text="◀️ Назад", callback_data="lead:form:cancel")
    builder.adjust(1)
    return builder.as_markup()


def build_lead_done_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 В главное меню", callback_data="nav:home")
    return builder.as_markup()
