from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

import httpx

from app.rates.models import CachedRate, RatePayload, RateQuery, RateSource
from app.rates.providers.base import BaseRateProvider


class GrinexProvider(BaseRateProvider):
    source = RateSource.GRINEX

    def __init__(self, client: httpx.AsyncClient, endpoint: str) -> None:
        super().__init__(client)
        # Default to a public, no-key endpoint for USD->RUB if GRINEX_ENDPOINT is not set
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
            if "rates" in data and "RUB" in data["rates"]:
                value = Decimal(str(data["rates"]["RUB"]))
            elif isinstance(data.get("price"), (int, float, str)):
                value = Decimal(str(data["price"]))
            else:
                raise ValueError("Unsupported response format for Grinex endpoint")
        except Exception:
            # Public fallback via shared helper
            value, raw = await self.fetch_usd_to_rub_no_key()

        payload = RatePayload(
            source=self.source,
            method=query.method,
            geo=query.geo,
            mode=query.mode,
            depth=query.depth,
            value=value,
            updated_at=datetime.now(timezone.utc),
            extras={"endpoint": self.endpoint, "note": "public-no-key"},
        )
        return CachedRate(payload=payload, raw_source=raw)
