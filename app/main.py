from __future__ import annotations

import asyncio

import httpx
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from app.core.bot import create_bot, create_dispatcher, setup_dispatcher, shutdown_bot
from app.core.config import Settings, get_settings
from app.core.db import create_engine, create_session_factory
from app.core.logging import setup_logging
from app.core.redis import close_redis, create_redis
from app.handlers import register_handlers
from app.rates.models import RateSource
from app.rates.providers.bybit import BybitProvider
from app.rates.providers.grinex import GrinexProvider
from app.rates.providers.rapira import RapiraProvider
from app.rates.service import RateService
from app.services.aml.service import AMLService
from app.services.aml.providers import GetBlockProvider, GetBlockAmlProvider
from app.services.leads.service import LeadService


async def _build_dispatcher(settings: Settings) -> tuple[Dispatcher, RateService, AMLService, LeadService]:
    redis = create_redis(settings.redis_url)
    storage = RedisStorage(redis=redis)
    dp = create_dispatcher(storage=storage)

    http_client = httpx.AsyncClient(timeout=10.0)

    providers = {
        RateSource.BYBIT: BybitProvider(http_client, settings.bybit_endpoint),
        RateSource.RAPIRA: RapiraProvider(http_client, settings.rapira_endpoint),
        RateSource.GRINEX: GrinexProvider(http_client, settings.grinex_endpoint),
    }

    rate_service = RateService(redis=redis, providers=providers, settings=settings)

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    lead_service = LeadService(session_factory=session_factory)
    # AML provider selection
    if settings.getblock_aml_token:
        aml_provider = GetBlockAmlProvider(
            http_client,
            settings.getblock_base_url or "https://api.getblock.net/rpc/v1/request",
            settings.getblock_aml_token.get_secret_value(),
            evm_probe_order=[s.strip() for s in (settings.getblock_evm_probe_order or "ETH,BSC,MATIC,ETC").split(",")],
            default_evm_chain=settings.getblock_default_evm_chain or "ETH",
            timeout_sec=float(settings.getblock_request_timeout_sec or 8.0),
            poll_attempts=int(settings.getblock_poll_attempts or 10),
            poll_delay_ms=int(settings.getblock_poll_delay_ms or 1500),
        )
        aml_service = AMLService(provider=aml_provider)
    elif settings.getblock_api_key:
        aml_provider = GetBlockProvider(
            http_client,
            settings.getblock_base_url or "https://api.getblock.net/rpc/v1/request",
            settings.getblock_api_key.get_secret_value(),
            chain="ETH",
            blockchain=(settings.getblock_blockchain or "eth"),
            network=(settings.getblock_network or "mainnet"),
        )
        aml_service = AMLService(provider=aml_provider)
    else:
        aml_service = AMLService()

    dp["settings"] = settings
    dp["rate_service"] = rate_service
    dp["lead_service"] = lead_service
    dp["aml_service"] = aml_service
    dp["http_client"] = http_client
    dp["redis"] = redis
    dp["engine"] = engine
    dp["session_factory"] = session_factory

    setup_dispatcher(dp)
    register_handlers(dp)

    return dp, rate_service, aml_service, lead_service


async def run() -> None:
    settings = get_settings()
    setup_logging()
    bot = create_bot(settings.bot_token.get_secret_value())
    bot.default = DefaultBotProperties(parse_mode=ParseMode.HTML)

    dp, _, _, _ = await _build_dispatcher(settings)

    try:
        await dp.start_polling(bot)
    finally:
        await shutdown(dp, bot)


async def shutdown(dp: Dispatcher, bot: Bot) -> None:
    http_client: httpx.AsyncClient = dp["http_client"]
    redis = dp["redis"]
    engine = dp["engine"]

    await http_client.aclose()
    await close_redis(redis)
    await engine.dispose()
    await dp.storage.close()
    await dp.storage.wait_closed()
    await shutdown_bot(bot)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
