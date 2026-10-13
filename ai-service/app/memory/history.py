"""会话历史存储：Redis list `chat:{user}:{session}`（键名与 v2 一致）。

迁移自 v2 core/redis_memory.py 会话历史部分：
- 每条消息 json 序列化后 RPUSH（含 role/content/timestamp）
- TTL 7 天（每次写入刷新）
- 裁剪：长度超过 MEMORY_MAX_TURNS*2 条时只保留最近这么多条
- user_id/session_id 一律转 str 后拼 key
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.memory import get_redis

CONVERSATION_TTL = 86400 * 7


def _conversation_key(user_id: str, session_id: str) -> str:
    return f"chat:{str(user_id)}:{str(session_id)}"


async def add_message(
    user_id: str, session_id: str, role: str, content: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """追加一条消息，并刷新 TTL / 按上限裁剪。

    extra 为前端展示用的结构化附件（cards/citations/draft），随消息一起持久化；
    LLM 上下文构建（get_history_context）只读 content，不受 extra 影响。
    """
    client = get_redis()
    key = _conversation_key(user_id, session_id)

    message_dict: Dict[str, Any] = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
    }
    if extra:
        message_dict.update(extra)

    await client.rpush(key, json.dumps(message_dict, ensure_ascii=False))
    await client.expire(key, CONVERSATION_TTL)

    max_messages = settings.MEMORY_MAX_TURNS * 2
    current_len = await client.llen(key)
    if current_len > max_messages:
        await client.ltrim(key, -max_messages, -1)


async def get_history(
    user_id: str, session_id: str, limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """读最近 limit 条消息（默认 MEMORY_MAX_TURNS*2，坏数据跳过，同 v2）。"""
    client = get_redis()
    key = _conversation_key(user_id, session_id)

    limit = limit or settings.MEMORY_MAX_TURNS * 2
    messages = await client.lrange(key, -limit, -1)

    result: List[Dict[str, Any]] = []
    for msg in messages:
        try:
            result.append(json.loads(msg))
        except json.JSONDecodeError:
            continue
    return result


async def get_history_context(user_id: str, session_id: str) -> str:
    """把会话历史拼成「用户/助手: 内容」文本（同 v2 get_conversation_context）。"""
    messages = await get_history(user_id, session_id)
    if not messages:
        return ""

    lines = []
    for msg in messages:
        role = "用户" if msg.get("role") == "user" else "助手"
        lines.append(f"{role}: {msg.get('content', '')}")
    return "\n".join(lines)


async def clear_session(user_id: str, session_id: str) -> None:
    """删除单个会话的全部历史。"""
    client = get_redis()
    await client.delete(_conversation_key(user_id, session_id))


async def clear_all(user_id: str) -> None:
    """清空用户全部会话历史（v2 clear_all 中会话部分；偏好清理在 profile）。"""
    client = get_redis()
    keys = []
    async for key in client.scan_iter(match=f"chat:{str(user_id)}:*"):
        keys.append(key)
    if keys:
        await client.delete(*keys)
