"""安全横切层：用户身份识别 / 限流 / SSE 连接槽位 / 输入清洗与注入检测。"""
import re
import time
import uuid

from fastapi import HTTPException, Request

from app.core.config import settings
from app.core.observability import rate_limited_total


def get_request_user(request: Request) -> str:
    """FastAPI 依赖：识别请求用户。X-User-Id 头优先 → user_id query 回退 → 401。"""
    user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="未识别用户身份")
    return user_id


async def check_rate_limit(redis_client, user_id: str) -> None:
    """限流：per-user 滑动窗口（ZSET 毫秒时间戳）+ 全局固定窗口（INCR 秒级时间片）。

    超限抛 HTTPException(429)。redis_client 为 None 时放行（未配置 Redis 降级直通）。
    """
    if redis_client is None:
        return

    # per-user 滑动窗口：ZADD 当前毫秒 → 清理 60s 前成员 → ZCARD 判断
    now_ms = int(time.time() * 1000)
    user_key = f"rl:{user_id}"
    member = f"{now_ms}:{uuid.uuid4().hex}"
    pipe = redis_client.pipeline()
    pipe.zadd(user_key, {member: now_ms})
    pipe.zremrangebyscore(user_key, 0, now_ms - 60_000)
    pipe.zcard(user_key)
    # 兜底 TTL：用户不再请求后 key 自动清理
    pipe.expire(user_key, 120)
    results = await pipe.execute()
    user_count = results[2]
    if user_count > settings.RATE_LIMIT_USER_PER_MIN:
        rate_limited_total.labels(scope="user").inc()
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    # 全局固定窗口：INCR 秒级时间片，首个请求设置 2s 兜底 TTL
    global_key = f"rl:global:{int(time.time())}"
    global_count = await redis_client.incr(global_key)
    if global_count == 1:
        await redis_client.expire(global_key, 2)
    if global_count > settings.RATE_LIMIT_GLOBAL_QPS:
        rate_limited_total.labels(scope="global").inc()
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")


async def acquire_sse_slot(redis_client, user_id: str) -> str:
    """占用一个 SSE 连接槽位（INCR + 120s TTL 兜底），超上限回滚并 429。返回 slot key。"""
    key = f"sseconn:{user_id}"
    if redis_client is None:
        return key

    count = await redis_client.incr(key)
    await redis_client.expire(key, 120)  # 兜底 TTL，防止异常退出导致计数残留
    if count > settings.SSE_MAX_CONN_PER_USER:
        await redis_client.decr(key)
        raise HTTPException(status_code=429, detail="SSE 连接数已达上限")
    return key


async def release_sse_slot(redis_client, user_id: str) -> None:
    """释放 SSE 连接槽位（DECR）。"""
    if redis_client is None:
        return
    await redis_client.decr(f"sseconn:{user_id}")


def sanitize_input(q: str) -> str:
    """输入清洗：去除首尾空白并按 INPUT_MAX_CHARS 截断。"""
    return q.strip()[: settings.INPUT_MAX_CHARS]


# 提示注入检测规则（忽略大小写，命中任一即判定）
_INJECTION_PATTERNS = [
    r"忽略(之前|以上|上面的)(所有)?指令",
    r"ignore\s+(all\s+)?previous",
    r"system\s+prompt",
    r"jailbreak",
    r"你现在是(管理员|系统|开发者模式)",
    r"DAN\s+mode",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def detect_injection(q: str) -> bool:
    """提示注入检测：命中规则列表任一返回 True。"""
    return bool(_INJECTION_RE.search(q))
