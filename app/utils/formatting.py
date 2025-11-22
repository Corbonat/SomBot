from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import NamedTuple, Optional

from app.rates.models import RatePayload


class BidAsk(NamedTuple):
    """Container for buy/sell prices (bid is sell, ask is buy)."""

    bid: Decimal
    ask: Decimal


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
    mosca_pair: Optional[BidAsk],
    bybit_mid: Optional[RatePayload],
    bybit_p2p: Optional[BidAsk],
) -> str:
    """Формирует общий дашборд курсов в требуемом формате."""
    lines = ["Общий Dashboard", "USDT/RUB", ""]

    if grinex_rate:
        lines.append(f"📊 Grinex — {grinex_rate.value:.2f}₽")
        lines.append("")

    if rapira_rate:
        lines.append(f"📊 Rapira — {rapira_rate.value:.2f}₽")
        lines.append("")

    if mosca_pair:
        lines.append("📊 Mosca")
        lines.append(f"купить USDT — {mosca_pair.ask:.2f}")
        lines.append(f"продать USDT — {mosca_pair.bid:.2f}")
        lines.append("")

    if bybit_mid or mosca_pair:
        lines.append("📊 Bybit (средний)")
        if bybit_mid:
            lines.append(f"Купить USDT — {bybit_mid.value:.2f}")
            lines.append(f"Продать USDT — {bybit_mid.value:.2f}")
        else:
            # Fallback to spot bid/ask if средний курс недоступен
            lines.append(f"Купить USDT — {mosca_pair.ask:.2f}" if mosca_pair else "Купить USDT — —")
            lines.append(f"Продать USDT — {mosca_pair.bid:.2f}" if mosca_pair else "Продать USDT — —")
        lines.append("")

    lines.append("📊 Bybit (последний курс P2P стакана)")
    if bybit_p2p:
        lines.append(f"Купить USDT — {bybit_p2p.ask:.2f}")
        lines.append(f"Продать USDT — {bybit_p2p.bid:.2f}")
    else:
        lines.append("Данные пока отсутствуют (нужен запрос к P2P API).")

    return "\n".join(lines).strip()
