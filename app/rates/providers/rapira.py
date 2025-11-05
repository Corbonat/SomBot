from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

import httpx

from app.rates.models import CachedRate, RateMethod, RatePayload, RateQuery, RateSource
from app.rates.providers.base import BaseRateProvider


class RapiraProvider(BaseRateProvider):
    source = RateSource.RAPIRA

    def __init__(self, client: httpx.AsyncClient, endpoint: str) -> None:
        super().__init__(client)
        # Default to a public, no-key endpoint for USD->RUB if RAPIRA_ENDPOINT is not set
        self.endpoint = (
            endpoint or "https://api.exchangerate.host/latest?base=USD&symbols=RUB"
        )

    async def fetch(self, query: RateQuery) -> CachedRate:
        async def _get_json(url: str) -> Dict[str, Any]:
            resp = await self.client.get(url)
            resp.raise_for_status()
            return resp.json()

        raw: Dict[str, Any] = {}
        try:
            data = await _get_json(self.endpoint)
            raw = data
                                                         
            # 1) Native Rapira open API shape
            #    { "data": [ { "symbol": "USDT/RUB", "askPrice": 82.43, "bidPrice": 82.42, ... } ], ... }
            if isinstance(data.get("data"), list):
                items = [item for item in data["data"] if isinstance(item, dict)]
                def _is_usdtrub(item: Dict[str, Any]) -> bool:
                    symbol = str(item.get("symbol", ""))
                    base = str(item.get("baseCurrency", "")).upper()
                    quote = str(item.get("quoteCurrency", "")).upper()
                    return (
                        symbol.upper() in {"USDT/RUB", "USDTRUB", "USDT_RUB"}
                        or (base == "RUB" and quote == "USDT")
                    )
                target = next((it for it in items if _is_usdtrub(it)), None)
                if target:
                    ask = target.get("askPrice")
                    bid = target.get("bidPrice")
                    close = target.get("close")
                    if ask is not None and bid is not None:
                        value = (Decimal(str(ask)) + Decimal(str(bid))) / Decimal("2")
                    elif close is not None:
                        value = Decimal(str(close))
                    else:
                        raise ValueError("Rapira data item missing ask/bid/close")
                    extras = {
                        "symbol": target.get("symbol"),
                        "ask": ask,
                        "bid": bid,
                    }
                else:
                    raise ValueError("USDT/RUB not found in Rapira data list")

            # 2) exchangerate.host and similar (fallback if endpoint is not Rapira)
            elif "rates" in data and "RUB" in data["rates"]:
                value = Decimal(str(data["rates"]["RUB"]))
                extras = {}

            # 3) Generic single-number price
            elif isinstance(data.get("price"), (int, float, str)):
                value = Decimal(str(data["price"]))
                extras = {}
            else:
                raise ValueError("Unsupported response format for Rapira endpoint")
        except Exception:
            # Public fallback via shared helper
            value, raw = await self.fetch_usd_to_rub_no_key()
            extras = {"fallback": True}

        payload = RatePayload(
            source=self.source,
            method=query.method if isinstance(query.method, RateMethod) else RateMethod(str(query.method)),
            geo=query.geo,
            mode=query.mode,
            depth=query.depth,
            value=value,
            updated_at=datetime.now(timezone.utc),
            extras={"endpoint": self.endpoint, "note": "public-no-key", **(extras or {})},
        )
        return CachedRate(payload=payload, raw_source=raw)
