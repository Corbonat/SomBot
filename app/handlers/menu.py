from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.common import nav_row
from app.keyboards.lead import build_lead_menu
from app.keyboards.main_menu import build_main_menu
from app.keyboards.rates import build_sources_menu
from app.utils.texts import get_text

router = Router(name="menu")


@router.callback_query(lambda c: c.data == "info:about")
async def show_about(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        get_text("menu.about"), reply_markup=nav_row().as_markup()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "rates")
async def open_rates(
    callback: CallbackQuery,
    rate_service: "RateService",
    settings: "Settings",
) -> None:
    from app.handlers.rates import _render_all_rates
    text = await _render_all_rates(rate_service, settings)
    await callback.message.edit_text(text, reply_markup=build_sources_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "education")
async def open_education(callback: CallbackQuery) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("education.buttons.academy"), callback_data="education:academy")
    builder.button(text=get_text("education.buttons.pin"), callback_data="education:pin")
    builder.adjust(1)
    builder.attach(nav_row())
    await callback.message.edit_text(
        get_text("education.title"), reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "hacker")
async def open_hacker(callback: CallbackQuery) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("hacker.open"), url=get_text("links.hacker_bot"))
    builder.button(text=get_text("hacker.ref"), callback_data="hacker:ref")
    builder.adjust(1)
    builder.attach(nav_row())
    await callback.message.edit_text(
        get_text("hacker.text"), reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "guides")
async def open_guides(callback: CallbackQuery) -> None:
    builder = InlineKeyboardBuilder()
    guides = get_text("guides.items")
    for key, item in guides.items():
        builder.button(text=item["title"], callback_data=f"guides:{key}")
    builder.adjust(1)
    builder.attach(nav_row())
    await callback.message.edit_text(get_text("guides.title"), reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(lambda c: c.data == "aml")
async def open_aml(callback: CallbackQuery) -> None:
    from app.keyboards.aml import build_aml_menu

    await callback.message.edit_text(get_text("aml.title"), reply_markup=build_aml_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "lead")
async def open_lead(callback: CallbackQuery) -> None:
    contact = str(get_text("links.contact"))
    handle = contact
    try:
        # Extract @username from typical Telegram URL formats
        if contact.startswith("http://") or contact.startswith("https://"):
            # Expected like https://t.me/username
            from urllib.parse import urlparse
            parsed = urlparse(contact)
            if parsed.netloc.endswith("t.me") and parsed.path:
                username = parsed.path.strip("/")
                if username:
                    handle = f"@{username}"
        elif contact.startswith("tg://"):
            # Fallback to showing raw tg link
            handle = contact
        elif not contact.startswith("@"):
            # If it's something else (e.g., plain username), normalize
            handle = f"@{contact}"
    except Exception:
        handle = contact

    text = f"Напишите сюда ({handle}) чтобы получить персонализированное предложение"
    await callback.message.edit_text(text, reply_markup=build_lead_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data in {"education:academy", "education:pin", "hacker:ref"})
async def stub(callback: CallbackQuery) -> None:
    from app.keyboards.common import nav_row
    await callback.message.edit_text(get_text("common.coming_soon"), reply_markup=nav_row().as_markup())
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("guides:"))
async def show_guide_item(callback: CallbackQuery) -> None:
    key = callback.data.split(":", 1)[1]
    items = get_text("guides.items")
    if key in items:
        from app.keyboards.common import nav_row
        await callback.message.edit_text(
            get_text("common.coming_soon"), reply_markup=nav_row().as_markup()
        )
        await callback.answer()
    else:
        await callback.answer("Раздел не найден", show_alert=True)


@router.callback_query(lambda c: c.data == "nav:back")
async def nav_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text(get_text("menu.start"), reply_markup=build_main_menu())
    await callback.answer()
