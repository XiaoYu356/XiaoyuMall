"""用户偏好存储：Redis hash `pref:{user}`（键名与 v2 一致，保证遗留数据可读）。

v3.1 起把偏好从"每字段覆盖写"改为"原子条目 + 时间戳追加"：
- 每个条目 {"k": 字段, "v": 值, "ts": 写入时间戳}，整体 json 序列化存 hash 的 `items` 字段
- 列表型偏好（品类/品牌）拆成单值条目，便于按相关性挑 top-k 注入
- 相同 (k, v) 只刷新时间戳，不重复写入；总条目数封顶 MAX_ITEMS，超出淘汰最旧
- 读取时按"时间衰减 + 与当前问题的字面重合度"排序，只注入 top-k，
  避免每轮把全部偏好塞进上下文（企业记忆层的常见做法）
- 遗留数据（hash 里直接存 favorite_categories/price_range 等字段）读取时自动兼容
- TTL 30 天，每次写入刷新
"""
import json
import time
from typing import Any, Dict, List

from app.memory import get_redis

PREFERENCE_TTL = 86400 * 30
MAX_ITEMS = 50

_ITEMS_FIELD = "items"
# v2 遗留字段（仅作为兜底读取来源）
_LEGACY_FIELDS = ("favorite_categories", "price_range", "favorite_brands", "other_notes")
# 列表型偏好：写入时拆成单值条目，聚合读取时还原为列表
_LIST_FIELDS = {"favorite_categories", "favorite_brands"}


def _preference_key(user_id: str) -> str:
    return f"pref:{user_id}"


def _now() -> float:
    return time.time()


def _flatten(field: str, value: Any) -> List[Any]:
    """把一次写入的字段值拆成原子值列表（列表字段逐项拆，其余单值）。

    兼容 v2 写法：列表字段可能以 JSON 字符串传入（如 '["手机","耳机"]'）。
    """
    if field in _LIST_FIELDS and isinstance(value, str) and value.strip().startswith("["):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
    if field in _LIST_FIELDS:
        if isinstance(value, (list, tuple, set)):
            return [v for v in value if str(v).strip()]
        return [value] if str(value).strip() else []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value] if str(value).strip() else []


def _merge_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """去重（同 k+v 刷新 ts）并按 ts 排序，保留最近 MAX_ITEMS 条。"""
    deduped: Dict[str, Dict[str, Any]] = {}
    for item in items:
        key = f"{item.get('k')}\u0000{json.dumps(item.get('v'), ensure_ascii=False, sort_keys=True)}"
        prev = deduped.get(key)
        if prev is None or float(item.get("ts") or 0) > float(prev.get("ts") or 0):
            deduped[key] = item
    merged = sorted(deduped.values(), key=lambda i: float(i.get("ts") or 0))
    return merged[-MAX_ITEMS:]


async def _load_items(user_id: str) -> List[Dict[str, Any]]:
    """读原子条目；新格式缺失时从 v2 遗留字段构造（ts=0，排序上天然让位给新数据）。"""
    client = get_redis()
    raw = await client.hget(_preference_key(user_id), _ITEMS_FIELD)
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [i for i in data if isinstance(i, dict) and "k" in i]
        except json.JSONDecodeError:
            pass

    legacy = await client.hmget(_preference_key(user_id), list(_LEGACY_FIELDS))
    items: List[Dict[str, Any]] = []
    for field, value in zip(_LEGACY_FIELDS, legacy):
        if value is None:
            continue
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = value
        for v in _flatten(field, parsed):
            items.append({"k": field, "v": v, "ts": 0})
    return items


async def _save_items(user_id: str, items: List[Dict[str, Any]]) -> None:
    client = get_redis()
    key = _preference_key(user_id)
    await client.hset(key, _ITEMS_FIELD, json.dumps(items, ensure_ascii=False))
    await client.expire(key, PREFERENCE_TTL)


async def add_preferences(user_id: str, updates: Dict[str, Any]) -> None:
    """批量追加偏好（整理器一次调用，减少 Redis 往返）。"""
    if not updates:
        return
    existing = await _load_items(user_id)
    ts = _now()
    new_items = list(existing)
    for field, value in updates.items():
        for v in _flatten(field, value):
            new_items.append({"k": field, "v": v, "ts": ts})
    await _save_items(user_id, _merge_items(new_items))


async def set_preference(user_id: str, field: str, value: Any) -> None:
    """写单条偏好（追加语义；同名同值只刷新时间戳）。"""
    await add_preferences(user_id, {field: value})


def _recency_score(ts: float) -> float:
    """30 天半衰期的时间衰减，范围 (0, 1]。"""
    age = max(0.0, _now() - float(ts or 0))
    return 0.5 ** (age / PREFERENCE_TTL)


def _bigrams(text: str) -> set:
    text = "".join(ch for ch in text if not ch.isspace())
    if len(text) < 2:
        return set(text)
    return {text[i:i + 2] for i in range(len(text) - 1)}


def _overlap_score(query: str, value: Any) -> float:
    """查询与偏好值的字面重合度（中文用 bigram，无需额外向量化依赖）。"""
    if not query:
        return 0.0
    q = _bigrams(query)
    v = _bigrams(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)
    if not q or not v:
        return 0.0
    return len(q & v) / len(q)


async def get_relevant_preferences(
    user_id: str, query: str = "", top_k: int = 5
) -> List[Dict[str, Any]]:
    """按相关性取 top-k 原子偏好，供 prompt 注入（返回 [{"k","v","ts"}]）。"""
    items = await _load_items(user_id)
    if not items:
        return []
    scored = [
        (
            0.6 * _recency_score(item.get("ts") or 0)
            + 0.4 * _overlap_score(query, item.get("v")),
            item,
        )
        for item in items
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[: max(1, top_k)]]


async def get_preferences(user_id: str) -> Dict[str, Any]:
    """聚合为 v2 兼容结构：列表字段还原为列表，其余取最新值。"""
    items = await _load_items(user_id)
    result: Dict[str, Any] = {}
    for item in sorted(items, key=lambda i: float(i.get("ts") or 0)):
        field, value = item.get("k"), item.get("v")
        if field in _LIST_FIELDS:
            result.setdefault(field, [])
            if value not in result[field]:
                result[field].append(value)
        else:
            result[field] = value
    return result


async def get_preference(user_id: str, field: str) -> Any:
    """读单个偏好字段的最新值（不存在返回 None）。"""
    items = await _load_items(user_id)
    values = [i for i in items if i.get("k") == field]
    if not values:
        return None
    latest = max(values, key=lambda i: float(i.get("ts") or 0))
    if field in _LIST_FIELDS:
        return [i.get("v") for i in sorted(values, key=lambda i: float(i.get("ts") or 0))]
    return latest.get("v")


async def delete_preference(user_id: str, field: str) -> None:
    """删除某个字段的全部条目（兼容清理遗留字段）。"""
    items = await _load_items(user_id)
    kept = [i for i in items if i.get("k") != field]
    client = get_redis()
    key = _preference_key(user_id)
    await client.hdel(key, field)
    if kept:
        await _save_items(user_id, kept)
    else:
        await client.delete(key)


async def clear_preferences(user_id: str) -> None:
    """清空用户全部偏好（删除整个 hash）。"""
    client = get_redis()
    await client.delete(_preference_key(user_id))
