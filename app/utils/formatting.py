from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import NamedTuple, Optional

from app.rates.models import RatePayload


class BidAsk(NamedTuple):
    """Container for buy/sell prices (bid is sell, ask is buy)."""

    bid: Decimal
    ask: Decimal


def _decimal_from(value: Optional[Decimal | float | str]) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _format_currency(value: Decimal) -> str:
    return f"{value:.2f}".replace(".", ",")


def _source_name(payload: RatePayload) -> str:
    mapping = {
        "rapira": "Rapira",
        "bybit": "Bybit",
        "grinex": "Grinex",
    }
    return mapping.get(payload.source.value, payload.source.value.capitalize())


def format_rate(payload: RatePayload) -> str:
    ask = _decimal_from(payload.extras.get("ask")) if payload.extras else None
    bid = _decimal_from(payload.extras.get("bid")) if payload.extras else None

    buy_value = ask or payload.value
    sell_value = bid or payload.value

    updated_at = payload.updated_at.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    source = _source_name(payload)

    return (
        f"💱 {source}\n\n"
        "Курс USDT/RUB\n\n"
        f"Купить {_format_currency(buy_value)}\n\n"
        f"Продать {_format_currency(sell_value)}\n\n"
        f"🔄 Обновлено {updated_at}"
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
