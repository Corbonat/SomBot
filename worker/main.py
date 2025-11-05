from __future__ import annotations

import asyncio

import httpx

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.redis import close_redis, create_redis
from app.rates.models import RateMethod, RateQuery, RateSource
from app.rates.providers.bybit import BybitProvider
from app.rates.providers.grinex import GrinexProvider
from app.rates.providers.rapira import RapiraProvider
from app.rates.service import RateService


async def warm_rates(rate_service: RateService) -> None:
    queries = {
        "bybit": RateQuery(source=RateSource.BYBIT, method=RateMethod.VWAP),
        "rapira": RateQuery(source=RateSource.RAPIRA, method=RateMethod.MID),
        "grinex": RateQuery(source=RateSource.GRINEX, method=RateMethod.MID),
    }
    while True:
        await rate_service.warm_up(queries)
        await asyncio.sleep(10)


async def main() -> None:
    settings = get_settings()
    setup_logging()

    redis = create_redis(settings.redis_url)
    http_client = httpx.AsyncClient(timeout=10.0)

    providers = {
        RateSource.BYBIT: BybitProvider(http_client, settings.bybit_endpoint),
        RateSource.RAPIRA: RapiraProvider(http_client, settings.rapira_endpoint),
        RateSource.GRINEX: GrinexProvider(http_client, settings.grinex_endpoint),
    }

    rate_service = RateService(redis=redis, providers=providers, settings=settings)

    try:
        await warm_rates(rate_service)
    finally:
        await http_client.aclose()
        await close_redis(redis)


if __name__ == "__main__":
    asyncio.run(main())
