"""安全横切层：用户身份识别 / 限流 / SSE 连接槽位 / 输入清洗与注入检测。"""
import re
import time

from fastapi import HTTPException, Request

from app.core.config import settings
from app.core.observability import rate_limited_total


# 令牌桶 Lua 脚本：HMSET/HMGET 读写桶状态（tokens + last_ms），按时间差补充令牌，
# 尝试扣 1 个令牌；Lua 保证"补充 + 扣减 + 写回"的原子性，避免并发下的竞态。
# 返回 1 = 放行，0 = 拒绝。
_TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])
local ttl_ms = tonumber(ARGV[4])

local bucket = redis.call('HMGET', key, 'tokens', 'last_ms')
local tokens = tonumber(bucket[1])
local last_ms = tonumber(bucket[2])

-- 首次初始化：满桶
if tokens == nil then
    tokens = capacity
    last_ms = now_ms
end

-- 按时间差补充令牌，不超过容量
local elapsed = (now_ms - last_ms) / 1000.0
if elapsed > 0 then
    tokens = math.min(capacity, tokens + elapsed * rate)
end

-- 尝试取一个令牌
local allowed = 0
if tokens >= 1 then
    tokens = tokens - 1
    allowed = 1
end

redis.call('HMSET', key, 'tokens', tokens, 'last_ms', now_ms)
redis.call('PEXPIRE', key, ttl_ms)

return allowed
"""


async def get_request_user(request: Request) -> str:
    """FastAPI 依赖：识别请求用户。

    优先读 satoken 头/query → 查 Redis ``satoken:login:token:{satoken}`` 拿 loginId
    （Gateway 已校验存在性，此处再查一次取 userId，防止绕过网关直连）；
    回退 X-User-Id 头 / user_id query（内部服务直连场景）；都无 → 401。
    """
    satoken = request.headers.get("satoken") or request.query_params.get("satoken")
    if satoken:
        from app.memory import get_redis

        redis = get_redis()
        try:
            login_id = await redis.get(f"satoken:login:token:{satoken}")
        except Exception:
            login_id = None
        if login_id:
            # sa-token-redis-jackson 存 Long loginId 为纯数字；String 则带引号，统一清洗
            return str(login_id).strip('"')
    # 回退：内部服务直连（X-Internal-Secret 已由上游网关校验）
    user_id = request.headers.get("X-User-Id") or request.query_params.get("user_id")
    if user_id:
        return user_id
    raise HTTPException(status_code=401, detail="未识别用户身份")


async def check_rate_limit(redis_client, user_id: str) -> None:
    """限流：per-user 令牌桶 + 全局令牌桶（Redis Lua 原子实现）。

    令牌桶允许瞬时突发（最多 capacity 个），同时按固定速率匀速补充令牌，
    兼顾突发流量友好性与长期稳态限流。Lua 脚本保证"补充 + 扣减 + 写回"原子性。
    超限抛 HTTPException(429)。redis_client 为 None 时放行（未配置 Redis 降级直通）。
    """
    if redis_client is None:
        return

    now_ms = int(time.time() * 1000)

    # per-user 令牌桶：容量 = RATE_LIMIT_USER_BURST，速率 = PER_MIN/60 个/秒
    user_rate = settings.RATE_LIMIT_USER_PER_MIN / 60.0
    user_key = f"rl:user:{user_id}"
    allowed = await redis_client.eval(
        _TOKEN_BUCKET_LUA,
        1,
        user_key,
        settings.RATE_LIMIT_USER_BURST,
        user_rate,
        now_ms,
        120_000,  # 兜底 TTL 120s，用户不再请求后桶自动清理
    )
    if not int(allowed):
        rate_limited_total.labels(scope="user").inc()
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    # 全局令牌桶：容量 = RATE_LIMIT_GLOBAL_BURST，速率 = QPS 个/秒
    global_key = "rl:global"
    allowed = await redis_client.eval(
        _TOKEN_BUCKET_LUA,
        1,
        global_key,
        settings.RATE_LIMIT_GLOBAL_BURST,
        float(settings.RATE_LIMIT_GLOBAL_QPS),
        now_ms,
        10_000,  # 兜底 TTL 10s，全局桶常驻
    )
    if not int(allowed):
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
