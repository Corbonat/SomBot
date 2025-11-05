from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.common import nav_row
from app.rates.models import BybitMode, GeoOption, RateMethod
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


def build_bybit_controls(
    method: RateMethod,
    geo: GeoOption,
    mode: BybitMode,
    locale: str = "ru",
) -> InlineKeyboardMarkup:
    texts = get_text("rates.bybit", locale)
    builder = InlineKeyboardBuilder()
    selected_prefix = "✔️ "

    methods_texts = texts["methods"]

    def _method_label(option: RateMethod) -> str:
        label = methods_texts.get(option.value, option.value.upper())
        return f"{selected_prefix}{label}" if method == option else label

    for option in (RateMethod.MID, RateMethod.BEST, RateMethod.VWAP):
        builder.button(
            text=_method_label(option), callback_data=f"rates:bybit:method:{option.value}"
        )

    builder.button(
        text=texts["mode"].format(mode=mode.value), callback_data="rates:bybit:mode:cycle"
    )

    geo_texts = texts["geo"]
    geo_key_map = {
        GeoOption.RIO: "rio",
        GeoOption.BERLIN: "berlin",
        GeoOption.NONE: "off",
    }

    def _geo_label(option: GeoOption) -> str:
        key = geo_key_map[option]
        label = (
            geo_texts.get(key)
            or geo_texts.get(option.value)
            or (geo_texts.get(False) if option == GeoOption.NONE else None)
        )
        # Support legacy YAML where "off" was parsed as boolean False
        label = label or option.value
        return f"{selected_prefix}{label}" if geo == option else label

    for option in (GeoOption.RIO, GeoOption.BERLIN, GeoOption.NONE):
        builder.button(
            text=_geo_label(option), callback_data=f"rates:bybit:geo:{option.value}"
        )

    builder.adjust(3, 1, 3)
    builder.attach(nav_row(back_cb="rates", home_cb="nav:home"))
    return builder.as_markup()

