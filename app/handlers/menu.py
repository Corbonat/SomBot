from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery, FSInputFile
from pathlib import Path
from aiogram.utils.keyboard import InlineKeyboardBuilder
from redis.asyncio import Redis

from app.keyboards.common import nav_row
from app.keyboards.lead import build_lead_menu
from app.keyboards.main_menu import build_main_menu
from app.keyboards.rates import build_sources_menu
from app.utils.main_photo import set_main_photo
from app.utils.texts import get_text
from app.utils.telegram import edit_text_or_caption

router = Router(name="menu")


async def _send_guide(
    callback: CallbackQuery,
    text: str,
    file_path: str | None = None,
    back_cb: str = "nav:back",
) -> None:
    """
    Унифицированная отправка гайда:
    - редактирует текущее сообщение (или подпись) с HTML-текстом и кнопками «Назад» / «Домой»;
    - при наличии файла отправляет его отдельным сообщением (фото или документ).
    """
    # Навигация: «Назад» и «Домой»
    kb = nav_row(back_cb=back_cb).as_markup()

    # Если есть файл — пытаемся отправить ОДНО сообщение: файл + caption.
    # Предыдущее сообщение с кнопками удаляем, чтобы не копились «хвосты».
    if file_path:
        path = Path(file_path)
        if path.exists():
            try:
                await callback.message.delete()
            except Exception:
                ...
            fs = FSInputFile(path.as_posix())
            lower = path.suffix.lower()
            if lower in {".png", ".jpg", ".jpeg", ".webp"}:
                await callback.message.answer_photo(fs, caption=text, reply_markup=kb)
            else:
                await callback.message.answer_document(fs, caption=text, reply_markup=kb)
            await callback.answer()
            return

    # Если файла нет или путь неверный — просто обновляем текст с кнопками
    await edit_text_or_caption(callback.message, text, kb)
    await callback.answer()


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
    builder.attach(nav_row())
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
    builder = InlineKeyboardBuilder()
    guides = get_text("guides.items")
    for key, item in guides.items():
        builder.button(text=item["title"], callback_data=f"guides:{key}")
    builder.adjust(1)
    # Из списка гайдов «Назад» ведет в главное меню
    builder.attach(nav_row())
    await edit_text_or_caption(callback.message, get_text("guides.title"), builder.as_markup())
    await callback.answer()


@router.callback_query(lambda c: c.data == "aml")
async def open_aml(callback: CallbackQuery) -> None:
    from app.keyboards.aml import build_aml_menu
    await edit_text_or_caption(callback.message, get_text("aml.title"), build_aml_menu())
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
async def show_guide_item(callback: CallbackQuery, redis: Redis) -> None:
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
            drops_items = get_text("guides.items.drops.items")
            builder = InlineKeyboardBuilder()
            for sub_key, item in drops_items.items():
                builder.button(
                    text=item["title"],
                    callback_data=f"guides:drops:{sub_key}",
                )
            builder.adjust(1)
            # Внутри дроповодства «Назад» ведет на список всех гайдов
            builder.attach(nav_row(back_cb="nav:guides"))
            await edit_text_or_caption(callback.message, "📬 Дроповодство", builder.as_markup())
            await callback.answer()
            return

        # Конкретный пункт внутри "Дроповодства"
        sub_key = parts[2]
        drops_items = get_text("guides.items.drops.items")
        if sub_key in drops_items:
            # Берем HTML-текст из ru.yml и возвращаемся «Назад» к меню дроповодства
            try:
                text = get_text(f"guides.items.drops.items.{sub_key}.text")
            except KeyError:
                text = get_text("common.coming_soon")

            await _send_guide(callback, text, back_cb="nav:drops")
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

        # Для гайда по прогреву карт дополнительно меняем основную картинку
        if main_key == "warmup_2025":
            await set_main_photo(
                redis,
                callback.message.bot,
                callback.message.chat.id,
                "assets/guides/warmup_2025/photo_2025-11-21_15-33-35.jpg",
            )

        # Кнопка «Назад» из гайда ведет обратно к списку гайдов
        await _send_guide(callback, text, file_path, back_cb="nav:guides")
    else:
        await callback.answer("Раздел не найден", show_alert=True)


@router.callback_query(lambda c: c.data == "nav:back")
async def nav_back(callback: CallbackQuery, redis: Redis) -> None:
    # При «Назад» возвращаем главную картинку и главное меню
    await set_main_photo(redis, callback.message.bot, callback.message.chat.id, "assets/images/main.jpg")
    await edit_text_or_caption(callback.message, get_text("menu.start"), build_main_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "nav:guides")
async def nav_guides(callback: CallbackQuery, redis: Redis) -> None:
    """Назад из гайдов: восстановить основную картинку и показать список гайдов."""
    await set_main_photo(redis, callback.message.bot, callback.message.chat.id, "assets/images/main.jpg")

    builder = InlineKeyboardBuilder()
    guides = get_text("guides.items")
    for key, item in guides.items():
        builder.button(text=item["title"], callback_data=f"guides:{key}")
    builder.adjust(1)
    # Из списка гайдов «Назад» ведет в главное меню
    builder.attach(nav_row())
    await edit_text_or_caption(callback.message, get_text("guides.title"), builder.as_markup())
    await callback.answer()


@router.callback_query(lambda c: c.data == "nav:drops")
async def nav_drops(callback: CallbackQuery, redis: Redis) -> None:
    """Назад из внутренних гайдов дроповодства: вернуться в меню дроповодства и сбросить картинку."""
    await set_main_photo(redis, callback.message.bot, callback.message.chat.id, "assets/images/main.jpg")

    drops_items = get_text("guides.items.drops.items")
    builder = InlineKeyboardBuilder()
    for sub_key, item in drops_items.items():
        builder.button(
            text=item["title"],
            callback_data=f"guides:drops:{sub_key}",
        )
    builder.adjust(1)
    # Из дроповодства «Назад» ведет к списку всех гайдов
    builder.attach(nav_row(back_cb="nav:guides"))
    await edit_text_or_caption(callback.message, "📬 Дроповодство", builder.as_markup())
    await callback.answer()
    