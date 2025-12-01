from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery, FSInputFile
from pathlib import Path
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import TYPE_CHECKING

from app.keyboards.common import nav_row
from app.keyboards.lead import build_lead_menu
from app.keyboards.main_menu import build_main_menu
from app.keyboards.rates import build_sources_menu
from app.utils.texts import get_text
from app.utils.telegram import edit_text_or_caption, format_with_preview

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.rates.service import RateService

router = Router(name="menu")


async def _send_guide(
    callback: CallbackQuery,
    text: str,
    file_path: str | None = None,
    back_cb: str = "nav:guides",
    preview_url: str | None = None,
    with_preview: bool = True,
) -> None:
    """
    Унифицированная отправка гайда:
    - если есть файл, удаляет старое сообщение и отправляет файл/документ с caption и кнопками;
    - иначе просто обновляет текст текущего сообщения.
    """
    kb = nav_row(back_cb=back_cb).as_markup()

    if file_path:
        path = Path(file_path)
        if path.exists() and path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            try:
                await callback.message.delete()
            except Exception:
                ...
            fs = FSInputFile(path.as_posix())
            caption = format_with_preview(text, preview_url, with_preview)
            await callback.message.answer_document(fs, caption=caption, reply_markup=kb)
            await callback.answer()
            return

    await edit_text_or_caption(
        callback.message,
        text,
        kb,
        replace_media=True,
        preview_url=preview_url,
        with_preview=with_preview,
    )
    await callback.answer()


async def _render_guides_list(callback: CallbackQuery, replace_media: bool = False) -> None:
    builder = InlineKeyboardBuilder()
    guides = get_text("guides.items")
    for key, item in guides.items():
        builder.button(text=item["title"], callback_data=f"guides:{key}")
    builder.adjust(1)
    builder.attach(nav_row())
    await edit_text_or_caption(
        callback.message,
        get_text("guides.title"),
        builder.as_markup(),
        replace_media=replace_media,
    )


async def _render_drops_menu(callback: CallbackQuery, replace_media: bool = False) -> None:
    drops_items = get_text("guides.items.drops.items")
    builder = InlineKeyboardBuilder()
    for sub_key, item in drops_items.items():
        builder.button(text=item["title"], callback_data=f"guides:drops:{sub_key}")
    builder.adjust(1)
    builder.attach(nav_row(back_cb="nav:guides"))
    await edit_text_or_caption(
        callback.message,
        "📬 Дроповодство",
        builder.as_markup(),
        replace_media=replace_media,
    )


@router.callback_query(lambda c: c.data == "info:about")
async def show_about(callback: CallbackQuery) -> None:
    await edit_text_or_caption(callback.message, get_text("menu.about"), nav_row().as_markup())
    await callback.answer()


@router.callback_query(lambda c: c.data == "rates")
async def open_rates(
    callback: CallbackQuery,
    rate_service: "RateService",
    settings: "Settings",
) -> None:
    from app.handlers.rates import _render_all_rates
    text = await _render_all_rates(rate_service, settings)
    await edit_text_or_caption(callback.message, text, build_sources_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "education")
async def open_education(callback: CallbackQuery) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("education.buttons.academy"), callback_data="education:academy")
    builder.button(text=get_text("education.buttons.pin"), callback_data="education:pin")
    builder.adjust(1)
    builder.attach(nav_row(back_cb="nav:home", home_cb="nav:home"))
    await edit_text_or_caption(callback.message, get_text("education.title"), builder.as_markup())
    await callback.answer()


@router.callback_query(lambda c: c.data == "hacker")
async def open_hacker(callback: CallbackQuery) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("hacker.open"), url=get_text("links.hacker_bot"))
    builder.button(text=get_text("hacker.ref"), callback_data="hacker:ref")
    builder.adjust(1)
    builder.attach(nav_row())
    await edit_text_or_caption(callback.message, get_text("hacker.text"), builder.as_markup())
    await callback.answer()


@router.callback_query(lambda c: c.data == "guides")
async def open_guides(callback: CallbackQuery) -> None:
    await _render_guides_list(callback)
    await callback.answer()


@router.callback_query(lambda c: c.data == "aml")
async def open_aml(callback: CallbackQuery) -> None:
    from app.keyboards.aml import build_aml_menu
    await edit_text_or_caption(callback.message, get_text("aml.title"), build_aml_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "lead")
async def open_lead(callback: CallbackQuery) -> None:
    text = get_text("lead.promo")
    await edit_text_or_caption(callback.message, text, build_lead_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data in {"education:academy", "hacker:ref"})
async def stub(callback: CallbackQuery) -> None:
    from app.keyboards.common import nav_row
    await edit_text_or_caption(callback.message, get_text("common.coming_soon"), nav_row().as_markup())
    await callback.answer()

@router.callback_query(lambda c: c.data == "education:pin")
async def education_pin_info(callback: CallbackQuery) -> None:
    from app.keyboards.common import nav_row
    text = (
        "Для просмотра обучающих постов необходимо подписаться на канал и перейти в закрепленные сообщения.\n\n"
        "Ссылка: https://t.me/+Jkdt4TFlU8plNDc6"
    )
    await edit_text_or_caption(callback.message, text, nav_row().as_markup())
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("guides:"))
async def show_guide_item(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    # ожидаем форматы:
    # guides:<key>
    # guides:drops:<subkey>
    if len(parts) < 2:
        await callback.answer("Раздел не найден", show_alert=True)
        return

    main_key = parts[1]

    # Подраздел "📬 Дроповодство"
    if main_key == "drops":
        # Открытие подменю: guides:drops
        if len(parts) == 2:
            await _render_drops_menu(callback, replace_media=True)
            await callback.answer()
            return

        # Конкретный пункт внутри "Дроповодства"
        sub_key = parts[2]
        drops_items = get_text("guides.items.drops.items")
        if sub_key in drops_items:

            # Для остальных — берем HTML-текст из ru.yml
            try:
                text = get_text(f"guides.items.drops.items.{sub_key}.text")
            except KeyError:
                text = get_text("common.coming_soon")

            try:
                file_path = get_text(f"guides.items.drops.items.{sub_key}.file")
            except KeyError:
                file_path = None

            await _send_guide(callback, text, file_path=file_path, back_cb="nav:drops")
            return

        await callback.answer("Раздел не найден", show_alert=True)
        return

        # Обычные гайды (первые три + Альфа)
    items = get_text("guides.items")
    if main_key in items:
        # Пытаемся взять HTML‑текст и путь к файлу из ru.yml
        try:
            text = get_text(f"guides.items.{main_key}.text")
        except KeyError:
            text = get_text("common.coming_soon")

        try:
            file_path = get_text(f"guides.items.{main_key}.file")
        except KeyError:
            file_path = None

        try:
            preview_url = get_text(f"guides.items.{main_key}.preview_url")
        except KeyError:
            preview_url = None

        await _send_guide(
            callback,
            text,
            file_path,
            back_cb="nav:guides",
            preview_url=preview_url,
        )
    else:
        await callback.answer("Раздел не найден", show_alert=True)


@router.callback_query(lambda c: c.data == "nav:back")
async def nav_back(callback: CallbackQuery) -> None:
    await edit_text_or_caption(
        callback.message,
        get_text("menu.start"),
        build_main_menu(),
        replace_media=True,
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "nav:guides")
async def nav_guides(callback: CallbackQuery) -> None:
    await _render_guides_list(callback, replace_media=True)
    await callback.answer()


@router.callback_query(lambda c: c.data == "nav:drops")
async def nav_drops(callback: CallbackQuery) -> None:
    await _render_drops_menu(callback, replace_media=True)
    await callback.answer()
    