from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Awaitable, Callable, Dict, Tuple, TypeVar

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from app.rates.models import CachedRate, RateQuery, RateSource

T = TypeVar("T")


class BaseRateProvider(ABC):
    source: RateSource

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    @abstractmethod
    async def fetch(self, query: RateQuery) -> CachedRate:
        raise NotImplementedError

    async def fetch_usd_to_rub_no_key(self) -> Tuple[Decimal, Dict[str, Any]]:
        """Try several public, no-key FX sources for USD->RUB.

        Returns a tuple of (rate, raw_source_json).
        """
        endpoints = [
            # exchangerate.host
            "https://api.exchangerate.host/latest?base=USD&symbols=RUB",
            # open.er-api.com
            "https://open.er-api.com/v6/latest/USD",
            # frankfurter.app
            "https://api.frankfurter.app/latest?from=USD&to=RUB",
            # fawazahmed0/currency-api (cdn, community)
            "https://cdn.jsdelivr.net/gh/fawazahmed0/currency-api@1/latest/currencies/usd/rub.json",
        ]

        for url in endpoints:
            try:
                resp = await self.client.get(url)
                resp.raise_for_status()
                data = resp.json()
                # Try known shapes
                if isinstance(data, dict):
                    if "rates" in data and isinstance(data["rates"], dict) and "RUB" in data["rates"]:
                        return Decimal(str(data["rates"]["RUB"])), data
                    if "result" in data and isinstance(data["result"], dict) and "RUB" in data["result"]:
                        return Decimal(str(data["result"]["RUB"])), data
                    if "rub" in data:  # fawazahmed0 json shape
                        return Decimal(str(data["rub"])), data
                    if "RUB" in data:  # some APIs may flatten
                        return Decimal(str(data["RUB"])), data
                # As a last resort, if there's a numeric 'rate' field
                rate_val = data.get("rate") if isinstance(data, dict) else None
                if rate_val is not None:
                    return Decimal(str(rate_val)), data
            except Exception:
                continue
        raise RuntimeError("Failed to fetch USD->RUB from public endpoints")


async def request_with_retry(call: Callable[[], Awaitable[T]], attempts: int = 3) -> T:
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential_jitter(exp_base=0.3, multiplier=1, max=2),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        reraise=True,
    ):
        with attempt:
            return await call()
    raise RuntimeError("Retry loop exited unexpectedly")
