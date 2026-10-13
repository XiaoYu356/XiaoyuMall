"""Letta 式记忆闭环（v3）：对话结束后异步提取用户偏好，写入 Redis 偏好库。

闭环链路：
    读偏好注入 prompt -> 回答 -> 每新增 4 条消息后台整理 -> 写回偏好 -> 下轮生效

相对 v2 core/memory_consolidator.py 的核心改造：
- 游标从进程内 dict 改存 Redis（`memcur:{u}:{s}`），多实例部署安全、进程重启后可延续
- 防并发锁同样存 Redis（`memlock:{u}:{s}`，NX EX 60），多实例只有一个能触发整理
- 计数方式：用 `LLEN chat:{u}:{s}`（列表当前长度）与游标求差，无需调用方传新增条数，
  为实现最简者（调用方只需在写完历史后调 maybe_consolidate 即可）
"""
import asyncio
import logging
import uuid

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.memory import get_redis
from app.memory import history, profile

logger = logging.getLogger(__name__)

CONSOLIDATE_THRESHOLD = 4        # 新增消息数达到该值才触发整理
MAX_MESSAGES_FOR_EXTRACT = 20    # 单次提取最多回看的消息条数
CURSOR_TTL = 86400 * 7           # 游标随会话（7 天 TTL）一起自然过期

# 后台任务强引用，防止被 GC 回收
_background_tasks: set = set()


class UserPreferences(BaseModel):
    """从对话中提取的用户偏好（未提及的字段留空）。"""

    favorite_categories: list[str] = Field(
        default_factory=list, description="用户关注的商品品类"
    )
    price_range: str = Field(default="", description="价格区间偏好，如 3000-5000元")
    favorite_brands: list[str] = Field(default_factory=list, description="偏好品牌")
    other_notes: str = Field(default="", description="其他值得记住的偏好或约束")


_EXTRACT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """从对话记录中提取用户偏好，输出 json 对象。字段：
- favorite_categories：用户关注的商品品类列表，如 ["手机", "耳机"]
- price_range：价格区间偏好，如 "3000-5000元"，未提及则为空字符串
- favorite_brands：偏好品牌列表，未提及则为空列表
- other_notes：其他值得记住的偏好或约束（一句话），未提及则为空字符串

只提取用户明确表达或强烈暗示的偏好，不要臆测；宁缺勿滥。"""),
    ("human", "{conversation}"),
])


def _extract_llm() -> ChatOpenAI:
    """提取用模型：快速配置（关闭思考，低温度）。"""
    return ChatOpenAI(
        model=settings.OPENAI_MODEL_FAST,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
        temperature=0.0,
        extra_body={"enable_thinking": False},
    )


async def maybe_consolidate(user_id: str, session_id: str) -> None:
    """新增消息数（LLEN - 游标）达到阈值时，在后台整理记忆（不阻塞调用方）。

    游标/锁均在 Redis，多实例安全：
    - 抢不到 memlock 说明其他实例正在整理，直接返回
    - 先推进 memcur 再派发后台任务，避免并发请求重复触发
    """
    if not user_id:
        return
    try:
        user_id = str(user_id)
        session_id = str(session_id)
        redis = get_redis()
        cur_key = f"memcur:{user_id}:{session_id}"

        total = await redis.llen(f"chat:{user_id}:{session_id}")
        try:
            last = int(await redis.get(cur_key) or 0)
        except (TypeError, ValueError):
            last = 0
        diff = total - last
        if diff < 0:
            # 会话被清空或过期后游标失效（游标现持久化在 Redis，比 v2 进程内游标
            # 多了这种跨重启残留场景），按 0 重新起算
            diff = total
        if diff < CONSOLIDATE_THRESHOLD:
            return

        # 抢锁：多实例只有一个能触发（EX 60 兜底，异常时锁自然过期）
        lock_key = f"memlock:{user_id}:{session_id}"
        token = uuid.uuid4().hex
        if not await redis.set(lock_key, token, nx=True, ex=60):
            return

        # 先推进游标（失败不影响主流程，最多导致一次重复整理）
        try:
            await redis.set(cur_key, total, ex=CURSOR_TTL)
        except Exception as e:
            logger.warning("记忆整理游标推进失败(忽略): %s", e)

        task = asyncio.create_task(_extract_preferences(user_id, session_id, lock_key))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    except Exception as e:
        logger.warning("记忆整理调度失败(忽略): %s", e)


async def _extract_preferences(user_id: str, session_id: str, lock_key: str) -> None:
    """后台提取偏好并覆盖写（提取到的字段覆盖旧值，未提及的保留旧值）。"""
    try:
        msgs = await history.get_history(user_id, session_id)
        recent = msgs[-MAX_MESSAGES_FOR_EXTRACT:]
        conversation = "\n".join(
            f"{'用户' if m.get('role') == 'user' else '助手'}: {m.get('content', '')}"
            for m in recent
        )
        if not conversation.strip():
            return
        chain = _EXTRACT_PROMPT | _extract_llm().with_structured_output(
            UserPreferences, method="json_mode"
        )
        prefs = await chain.ainvoke({"conversation": conversation})

        updates = {}
        if prefs.favorite_categories:
            updates["favorite_categories"] = prefs.favorite_categories
        if prefs.price_range:
            updates["price_range"] = prefs.price_range
        if prefs.favorite_brands:
            updates["favorite_brands"] = prefs.favorite_brands
        if prefs.other_notes:
            updates["other_notes"] = prefs.other_notes

        for field, value in updates.items():
            await profile.set_preference(user_id, field, value)
        logger.info("记忆整理完成 user=%s 更新字段=%s", user_id, list(updates))
    except Exception as e:
        logger.warning("记忆整理失败(忽略): %s", e)
    finally:
        # 释放锁（EXPIRE 60s 兜底；此处置失败锁也会自然过期）
        try:
            await get_redis().delete(lock_key)
        except Exception:
            pass


def close_consolidator() -> None:
    """进程收尾：取消在途整理任务（简单实现，不等待其完成）。"""
    for task in list(_background_tasks):
        task.cancel()
    _background_tasks.clear()
