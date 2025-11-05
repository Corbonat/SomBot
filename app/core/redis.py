from __future__ import annotations

from redis.asyncio import Redis


def create_redis(url: str) -> Redis:
    return Redis.from_url(url, encoding="utf-8", decode_responses=False)


async def close_redis(client: Redis) -> None:
    await client.aclose()
    await client.connection_pool.disconnect()
