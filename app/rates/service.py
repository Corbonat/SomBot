from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional, Protocol

import orjson
from redis.asyncio import Redis

from app.core.config import Settings
from app.core.logging import get_logger
from app.rates.models import CachedRate, RatePayload, RateQuery, RateSource

log = get_logger(__name__)


class RateProvider(Protocol):
    async def fetch(self, query: RateQuery) -> CachedRate:
        raise NotImplementedError


class RateService:
    def __init__(self, redis: Redis, providers: Dict[RateSource, RateProvider], settings: Settings) -> None:
        self.redis = redis
        self.providers = providers
        self.settings = settings

    def _cache_key(self, query: RateQuery) -> str:
        geo = query.geo.value if hasattr(query.geo, "value") else query.geo
        mode = query.mode.value if hasattr(query.mode, "value") else query.mode
        method = query.method.value if hasattr(query.method, "value") else query.method
        return f"rate:{query.source.value}:{method}:{geo}:{mode}:{query.depth or 0}"

    async def _get_cached(self, key: str) -> Optional[RatePayload]:
        raw = await self.redis.get(key)
        if not raw:
            return None
        data = orjson.loads(raw)
        return RatePayload(**data)

    async def _store_cached(self, key: str, payload: RatePayload, ttl: int) -> None:
        # Use JSON mode to ensure types like Decimal and datetime are JSON-serializable
        await self.redis.set(key, orjson.dumps(payload.model_dump(mode="json")), ex=ttl)

    async def get_rate(self, query: RateQuery, *, force: bool = False) -> RatePayload:
        key = self._cache_key(query)
        ttl = self.settings.cache_ttl_per_source.model_dump().get(query.source.value, 30)
        if not force:
            cached = await self._get_cached(key)
            if cached:
                return cached

        provider = self.providers.get(query.source)
        if not provider:
            raise ValueError(f"Provider for source {query.source} is not configured")

        cached_rate = await provider.fetch(query)
        payload = cached_rate.payload
        await self._store_cached(key, payload, ttl=ttl)
        return payload

    async def warm_up(self, queries: Dict[str, RateQuery]) -> None:
        async def _warm(query: RateQuery) -> None:
            try:
                await self.get_rate(query, force=True)
            except Exception as exc:  # noqa: BLE001 - log and continue
                log.warning("Failed to warm cache", query=query.model_dump(), error=str(exc))

        await asyncio.gather(*(_warm(q) for q in queries.values()))

    @staticmethod
    def mark_stale(payload: RatePayload, ttl: int, warn_age: int) -> RatePayload:
        now = datetime.now(timezone.utc)
        age = (now - payload.updated_at).total_seconds()
        if age > warn_age:
            payload.stale = True
        if payload.valid_until and payload.valid_until < now:
            payload.stale = True
        return payload
