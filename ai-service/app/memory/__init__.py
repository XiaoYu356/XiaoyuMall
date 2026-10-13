"""记忆模块共享 Redis 客户端单例。

被 memory 三个子模块（profile/history/consolidator）与后续 api 层（限流等）共用：
懒创建、模块级单例、进程退出时经 lifespan 调 close_redis() 收尾。
"""
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

_client: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    """获取共享 Redis 异步客户端（懒创建单例，decode_responses=True 与 v2 一致）。"""
    global _client
    if _client is None:
        _client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )
    return _client


async def close_redis() -> None:
    """关闭共享客户端（lifespan 收尾用；未创建过则什么都不做）。"""
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:
            pass
        _client = None
