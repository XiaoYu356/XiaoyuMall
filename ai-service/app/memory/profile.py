"""用户偏好存储：Redis hash `pref:{user}`（键名与 v2 一致，保证遗留数据可读）。

迁移自 v2 core/redis_memory.py 偏好部分：
- 每个偏好字段作为 hash 的一个 field，值为 json.dumps(..., ensure_ascii=False) 序列化
- 整理器（consolidator）把 UserPreferences dict 平铺：逐字段调 set_preference 覆盖写
- TTL 30 天，每次写入刷新
"""
import json
from typing import Any, Dict

from app.memory import get_redis

PREFERENCE_TTL = 86400 * 30


def _preference_key(user_id: str) -> str:
    return f"pref:{user_id}"


async def set_preference(user_id: str, field: str, value: Any) -> None:
    """写单个偏好字段（值 json 序列化后存入 hash，并刷新 TTL）。"""
    client = get_redis()
    key = _preference_key(str(user_id))
    await client.hset(key, field, json.dumps(value, ensure_ascii=False))
    await client.expire(key, PREFERENCE_TTL)


async def get_preferences(user_id: str) -> Dict[str, Any]:
    """读全部偏好字段（各 field 值反序列化；非 json 的按原字符串返回）。"""
    client = get_redis()
    data = await client.hgetall(_preference_key(str(user_id)))
    result: Dict[str, Any] = {}
    for k, v in data.items():
        try:
            result[k] = json.loads(v)
        except json.JSONDecodeError:
            result[k] = v
    return result


async def get_preference(user_id: str, field: str) -> Any:
    """读单个偏好字段（不存在返回 None）。"""
    client = get_redis()
    value = await client.hget(_preference_key(str(user_id)), field)
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


async def delete_preference(user_id: str, field: str) -> None:
    """删除单个偏好字段。"""
    client = get_redis()
    await client.hdel(_preference_key(str(user_id)), field)


async def clear_preferences(user_id: str) -> None:
    """清空用户全部偏好（删除整个 hash）。"""
    client = get_redis()
    await client.delete(_preference_key(str(user_id)))
