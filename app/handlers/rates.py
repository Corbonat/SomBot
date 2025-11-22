from __future__ import annotations

from typing import Iterable, List

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.core.config import Settings
from app.keyboards.common import nav_row
from app.keyboards.rates import build_bybit_controls, build_rate_actions, build_sources_menu
from app.rates.models import BybitMode, GeoOption, RateMethod, RateQuery, RateSource
from app.rates.providers.bybit import BybitProvider
from app.rates.service import RateService
from app.utils.formatting import BidAsk, format_all_rates, format_rate
from app.utils.telegram import edit_text_or_caption
from app.utils.texts import get_text

router = Router(name="rates")

ALLOWED_SOURCES = {item.value for item in RateSource}
ALLOWED_METHODS = {item.value for item in RateMethod}
ALLOWED_GEO = {item.value for item in GeoOption}


def _parse_command_args(args: Iterable[str], settings: Settings) -> RateQuery:
    source = settings.default_source
    method = settings.default_method
    geo = settings.default_geo
    mode = settings.bybit_mode

    for arg in args:
        lower = arg.lower()
        if lower in ALLOWED_SOURCES:
            source = lower
        elif lower in ALLOWED_METHODS:
            method = lower
        elif lower in ALLOWED_GEO:
            geo = lower
        else:
            raise ValueError(f"Unknown parameter: {arg}")

    return RateQuery(
        source=RateSource(source),
        method=RateMethod(method),
        geo=GeoOption(geo),
        mode=BybitMode(mode),
    )


def _ttl_for_source(settings: Settings, source: RateSource) -> int:
    ttls = settings.cache_ttl_per_source.model_dump()
    return int(ttls.get(source.value, 30))


async def _render_rate(
    payload_query: RateQuery,
    rate_service: RateService,
    settings: Settings,
    force: bool = False,
) -> str:
    payload = await rate_service.get_rate(payload_query, force=force)
    ttl = _ttl_for_source(settings, payload_query.source)
    payload = RateService.mark_stale(payload, ttl=ttl, warn_age=settings.rate_warn_age_sec)
    return format_rate(payload)


@router.message(Command("курс"))
async def cmd_rate(message: Message, rate_service: RateService, settings: Settings) -> None:
    args: List[str] = message.text.split()[1:] if message.text else []
    try:
        query = _parse_command_args(args, settings)
    except ValueError as exc:
        await message.answer(get_text("rates.errors.invalid"))
        await message.answer(str(exc))
        return
    text = await _render_rate(query, rate_service, settings)
    await message.answer(text)


@router.message(Command("best"))
async def cmd_best(message: Message, rate_service: RateService, settings: Settings) -> None:
    target = str(message.text or "").split()
    side = target[1] if len(target) > 1 else "bid"
    if side not in ("bid", "ask"):
        await message.answer("Only bid/ask supported")
        return
    method = RateMethod.BEST
    query = RateQuery(
        source=RateSource.BYBIT,
        method=method,
        geo=GeoOption(settings.default_geo),
        mode=BybitMode(settings.bybit_mode),
    )
    text = await _render_rate(query, rate_service, settings)
    await message.answer(text)


async def _render_all_rates(
    rate_service: RateService,
    settings: Settings,
    force: bool = False,
) -> str:
    """Получает и форматирует все курсы вместе."""
    grinex_rate = None
    rapira_rate = None
    mosca_pair: BidAsk | None = None
    bybit_mid = None
    bybit_p2p: BidAsk | None = None

    # Получаем курсы Grinex
    try:
        grinex_query = RateQuery(
            source=RateSource.GRINEX,
            method=RateMethod.MID,
            geo=GeoOption(settings.default_geo),
            mode=BybitMode.ORDERBOOK,
        )
        grinex_payload = await rate_service.get_rate(grinex_query, force=force)
        ttl = _ttl_for_source(settings, RateSource.GRINEX)
        grinex_rate = RateService.mark_stale(grinex_payload, ttl=ttl, warn_age=settings.rate_warn_age_sec)
    except Exception:
        pass
    
    # Получаем курсы Rapira
    try:
        rapira_query = RateQuery(
            source=RateSource.RAPIRA,
            method=RateMethod.MID,
            geo=GeoOption(settings.default_geo),
            mode=BybitMode.ORDERBOOK,
        )
        rapira_payload = await rate_service.get_rate(rapira_query, force=force)
        ttl = _ttl_for_source(settings, RateSource.RAPIRA)
        rapira_rate = RateService.mark_stale(rapira_payload, ttl=ttl, warn_age=settings.rate_warn_age_sec)
    except Exception:
        pass
    
    # Получаем средний курс Bybit (для блока "Bybit (средний)")
    try:
        bybit_mid_query = RateQuery(
            source=RateSource.BYBIT,
            method=RateMethod.MID,
            geo=GeoOption(settings.default_geo),
            mode=BybitMode(settings.bybit_mode),
        )
        bybit_mid_payload = await rate_service.get_rate(bybit_mid_query, force=force)
        ttl = _ttl_for_source(settings, RateSource.BYBIT)
        bybit_mid = RateService.mark_stale(bybit_mid_payload, ttl=ttl, warn_age=settings.rate_warn_age_sec)
    except Exception:
        pass
    
    # Получаем bid и ask от Bybit
    try:
        bybit_query = RateQuery(
            source=RateSource.BYBIT,
            method=RateMethod.BEST,
            geo=GeoOption(settings.default_geo),
            mode=BybitMode.ORDERBOOK,
        )
        provider = rate_service.providers.get(RateSource.BYBIT)
        if provider and isinstance(provider, BybitProvider):
            bid, ask = await provider.fetch_bid_ask(bybit_query)
            mosca_pair = BidAsk(bid=bid, ask=ask)
    except Exception:
        pass
    
    return format_all_rates(grinex_rate, rapira_rate, mosca_pair, bybit_mid, bybit_p2p)


@router.callback_query(lambda c: c.data == "rates")
async def open_rates_menu(
    callback: CallbackQuery,
    rate_service: RateService,
    settings: Settings,
) -> None:
    text = await _render_all_rates(rate_service, settings)
    await edit_text_or_caption(callback.message, text, build_sources_menu())
    await callback.answer()


async def _get_bybit_prefs(state: FSMContext, settings: Settings) -> dict:
    data = await state.get_data()
    prefs = data.get("bybit_prefs")
    if not prefs:
        prefs = {
            "method": settings.default_method,
            "geo": settings.default_geo,
            "mode": settings.bybit_mode,
        }
        await state.update_data(bybit_prefs=prefs)
    return prefs


async def _show_bybit_card(
    callback: CallbackQuery,
    rate_service: RateService,
    settings: Settings,
    state: FSMContext,
    force: bool = False,
) -> None:
    prefs = await _get_bybit_prefs(state, settings)
    query = RateQuery(
        source=RateSource.BYBIT,
        method=RateMethod(prefs["method"]),
        geo=GeoOption(prefs["geo"]),
        mode=BybitMode(prefs["mode"]),
    )
    text = await _render_rate(query, rate_service, settings, force=force)
    keyboard = build_bybit_controls(
        method=query.method,
        geo=query.geo,
        mode=query.mode,
    )
    await edit_text_or_caption(callback.message, text, keyboard)
    await callback.answer()


@router.callback_query(lambda c: c.data == "rates:bybit:menu")
async def bybit_menu(
    callback: CallbackQuery,
    rate_service: RateService,
    settings: Settings,
    state: FSMContext,
) -> None:
    await _show_bybit_card(callback, rate_service, settings, state)


@router.callback_query(lambda c: c.data.startswith("rates:bybit:method:"))
async def bybit_change_method(
    callback: CallbackQuery,
    rate_service: RateService,
    settings: Settings,
    state: FSMContext,
) -> None:
    prefs = await _get_bybit_prefs(state, settings)
    _, _, _, value = callback.data.split(":")
    prefs["method"] = value
    await state.update_data(bybit_prefs=prefs)
    await _show_bybit_card(callback, rate_service, settings, state)


@router.callback_query(lambda c: c.data.startswith("rates:bybit:geo:"))
async def bybit_change_geo(
    callback: CallbackQuery,
    rate_service: RateService,
    settings: Settings,
    state: FSMContext,
) -> None:
    prefs = await _get_bybit_prefs(state, settings)
    prefs["geo"] = callback.data.split(":")[-1]
    await state.update_data(bybit_prefs=prefs)
    await _show_bybit_card(callback, rate_service, settings, state)


@router.callback_query(lambda c: c.data == "rates:bybit:mode:cycle")
async def bybit_cycle_mode(
    callback: CallbackQuery,
    rate_service: RateService,
    settings: Settings,
    state: FSMContext,
) -> None:
    prefs = await _get_bybit_prefs(state, settings)
    order = [BybitMode.ORDERBOOK.value, BybitMode.P2P.value, BybitMode.COMPOSED.value]
    current = prefs.get("mode", settings.bybit_mode)
    idx = (order.index(current) + 1) % len(order)
    prefs["mode"] = order[idx]
    await state.update_data(bybit_prefs=prefs)
    await _show_bybit_card(callback, rate_service, settings, state)


@router.callback_query(lambda c: c.data.startswith("rates:rapira"))
async def rapira_actions(
    callback: CallbackQuery,
    rate_service: RateService,
    settings: Settings,
) -> None:
    force = callback.data.endswith(":refresh")
    query = RateQuery(
        source=RateSource.RAPIRA,
        method=RateMethod.MID,
        geo=GeoOption(settings.default_geo),
        mode=BybitMode.ORDERBOOK,
    )
    text = await _render_rate(query, rate_service, settings, force=force)
    await edit_text_or_caption(callback.message, text, build_rate_actions("rates:rapira"))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("rates:grinex"))
async def grinex_actions(
    callback: CallbackQuery,
    rate_service: RateService,
    settings: Settings,
) -> None:
    force = callback.data.endswith(":refresh")
    query = RateQuery(
        source=RateSource.GRINEX,
        method=RateMethod.MID,
        geo=GeoOption(settings.default_geo),
        mode=BybitMode.ORDERBOOK,
    )
    text = await _render_rate(query, rate_service, settings, force=force)
    await edit_text_or_caption(callback.message, text, build_rate_actions("rates:grinex"))
    await callback.answer()
