"""LangGraph checkpointer 解析：优先 AsyncRedisSaver（Redis 8 持久化），
连接/初始化失败时降级 MemorySaver，保证 ai-service 启动与对话不被 Redis 故障阻断。

AsyncRedisSaver 的构造可在事件循环外完成，但首次使用前必须 await asetup()
（建立连接、创建 checkpoint / writes 两个 RediSearch 索引）。
"""
import asyncio
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# asetup 含连接探测 + 索引创建，本地 Redis 正常时秒级完成
_SETUP_TIMEOUT_SECONDS = 5

_checkpointer: Any = None
_resolved = False
# 当前 checkpointer 模式：redis / memory / unknown（未初始化）
_mode: str = "unknown"


def _build_redis_url() -> str:
    password = f":{settings.REDIS_PASSWORD}@" if settings.REDIS_PASSWORD else ""
    return (
        f"redis://{password}{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        f"/{settings.REDIS_DB}"
    )


async def init_checkpointer() -> Any:
    """应用启动时调用一次：解析并初始化 checkpointer（单例）。"""
    global _checkpointer, _resolved, _mode
    if _resolved:
        return _checkpointer

    try:
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver

        saver = AsyncRedisSaver(_build_redis_url())
        # 连接不可达 / 模块缺失 / 建索引失败都会在此暴露
        await asyncio.wait_for(saver.asetup(), timeout=_SETUP_TIMEOUT_SECONDS)
        _checkpointer = saver
        _mode = "redis"
        logger.info(
            "LangGraph checkpointer=redis (%s:%s db=%s)",
            settings.REDIS_HOST,
            settings.REDIS_PORT,
            settings.REDIS_DB,
        )
    except Exception as e:
        from langgraph.checkpoint.memory import MemorySaver

        _checkpointer = MemorySaver()
        _mode = "memory"
        logger.warning(
            "Redis checkpointer 初始化失败，降级为内存模式（重启后会话状态丢失）: %s",
            e,
        )

    _resolved = True
    return _checkpointer


def checkpointer_mode() -> str:
    """返回当前 checkpointer 模式：redis / memory / unknown。"""
    return _mode
