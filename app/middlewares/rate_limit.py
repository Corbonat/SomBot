from __future__ import annotations

import time
from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from redis.asyncio import Redis


Handler = Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]]


class RateLimitMiddleware(BaseMiddleware):
    """Simple rate limiter based on Redis INCR with TTL."""

    def __init__(self, redis: Redis, prefix: str, limit: int, interval: float) -> None:
        self.redis = redis
        self.prefix = prefix
        self.limit = limit
        self.interval = interval

    async def __call__(self, handler: Handler, event: TelegramObject, data: Dict[str, Any]) -> Any:
        user_id = data.get("event_from_user").id if data.get("event_from_user") else None
        chat_id = data.get("event_chat").id if data.get("event_chat") else None
        if user_id is None:
            return await handler(event, data)

        key = f"{self.prefix}:{user_id}"
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, int(self.interval))
        if current > self.limit:
            data["rate_limited_at"] = time.time()
            return None
        return await handler(event, data)
