from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from app.rates.models import RatePayload


def format_rate(payload: RatePayload) -> str:
    updated_at = payload.updated_at.astimezone(timezone.utc).strftime("%H:%M:%S")
    stale_flag = " (устарело)" if payload.stale else ""
    geo = "" if payload.geo.value == "none" else f", Гео: {payload.geo.value}"
    depth = f"; depth={payload.depth}" if payload.depth else ""
    extras = ""
    if payload.extras:
        hidden_keys = {"note", "endpoint"}
        visible = [
            f"{key}: {value}"
            for key, value in payload.extras.items()
            if value is not None and key not in hidden_keys
        ]
        if visible:
            extras = "\n" + "\n".join(visible)
    return (
        f"USDT/RUB = {payload.value:.2f}\n"
        f"Источник: {payload.source.value}, Метод: {payload.method.value}, Режим: {payload.mode.value}{geo}{depth}\n"
        f"Обновлено: {updated_at}{stale_flag}{extras}"
    )


def format_all_rates(
    grinex_rate: Optional[RatePayload],
    rapira_rate: Optional[RatePayload],
    bybit_bid: Optional[Decimal],
    bybit_ask: Optional[Decimal],
) -> str:
    """Форматирует все курсы в единое сообщение."""
    lines = ["USDT/RUB:\n\n"]
    
    if grinex_rate:
        lines.append(f"🌙 Grinex\n{grinex_rate.value:.2f}₽\n\n")
    
    if rapira_rate:
        lines.append(f"🌙 Rapira\n{rapira_rate.value:.2f}₽\n\n")
    
    if bybit_bid is not None and bybit_ask is not None:
        lines.append(
            f"🌙 Mosca\nкупить USDT — {bybit_ask:.1f}\nпродать USDT — {bybit_bid:.1f}"
        )
    
    return "\n".join(lines)
