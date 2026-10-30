"""会话历史滚动摘要：替代"超预算直接丢弃"，把被裁剪的旧消息压成一段摘要。

链路：
    每轮对话结束 -> 用与模型输入相同的裁剪规则算出 dropped 消息
    -> 新增 dropped 达到 MIN_NEW_MESSAGES 条时，后台调快模型增量合并摘要
    -> 写 Redis `sum:{u}:{s}`（upto 记录已覆盖到哪条消息）
    -> 下一轮 chat.py 读出发给图，由 agent._pre_model_trim 注入到模型输入头部

设计约束：
- 只影响模型输入，不删 checkpoint（HITL interrupt/resume 依赖完整轨迹）
- 增量更新：已覆盖的消息不重复送模型，只在新增片段足够时才调用 LLM
- 锁 + 后台任务：多实例/同实例并发时只有一个整理，且不阻塞 SSE 收尾
- TTL 7 天，与 chat 历史列表对齐
"""
import asyncio
import hashlib
import json
import logging
import time
from typing import Any, List

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.memory import get_redis

logger = logging.getLogger(__name__)

SUMMARY_TTL = 86400 * 7
# 至少积攒 4 条（约两轮）新消息才值得再调一次模型，避免每轮都产生摘要开销
MIN_NEW_MESSAGES = 4
MAX_SUMMARY_CHARS = 800
MAX_INPUT_CHARS = 6000
MAX_MESSAGE_CHARS = 500
_LOCK_TTL = 60

# 后台任务强引用，防止被 GC 回收
_tasks: set = set()


def _key(user_id: str, session_id: str) -> str:
    return f"sum:{str(user_id)}:{str(session_id)}"


def _lock_key(user_id: str, session_id: str) -> str:
    return f"sumlock:{str(user_id)}:{str(session_id)}"


def _msg_key(msg: BaseMessage) -> str:
    """消息游标：优先用 LangChain 分配的 id，缺失时用内容哈希兜底。"""
    msg_id = getattr(msg, "id", None)
    if msg_id:
        return str(msg_id)
    raw = f"{getattr(msg, 'type', '')}:{_content_text(msg.content)}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block if isinstance(block, str) else str(block.get("text", ""))
            for block in content
            if isinstance(block, (str, dict))
        )
    return ""


def _conversation_text(messages: List[BaseMessage]) -> str:
    """拼出待摘要片段（跳过 SystemMessage，单条与总长都截断）。"""
    lines = []
    for msg in messages:
        if isinstance(msg, SystemMessage):
            continue
        role = "用户" if isinstance(msg, HumanMessage) else (
            "工具" if getattr(msg, "type", "") == "tool" else "助手"
        )
        text = _content_text(msg.content).strip()
        if not text:
            continue
        lines.append(f"{role}: {text[:MAX_MESSAGE_CHARS]}")
    joined = "\n".join(lines)
    return joined[-MAX_INPUT_CHARS:]


def _extract_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.OPENAI_MODEL_FAST,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
        temperature=0.0,
        extra_body={"enable_thinking": False},
    )


async def get_summary(user_id: str, session_id: str) -> str:
    """读当前会话摘要文本（不存在或损坏返回空串）。"""
    try:
        raw = await get_redis().get(_key(user_id, session_id))
        if not raw:
            return ""
        data = json.loads(raw)
        return str(data.get("text") or "")
    except Exception as e:
        logger.warning("读取会话摘要失败(忽略): %s", e)
        return ""


def schedule_summary_update(
    user_id: str, session_id: str, dropped: List[BaseMessage]
) -> None:
    """派发后台摘要更新（不阻塞 SSE 收尾）。"""
    if not dropped:
        return
    task = asyncio.create_task(maybe_update_summary(user_id, session_id, dropped))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def maybe_update_summary(
    user_id: str, session_id: str, dropped: List[BaseMessage]
) -> None:
    """把新被裁剪的消息增量合并进摘要（失败静默，摘要只是增强层）。"""
    redis = get_redis()
    lock_key = _lock_key(user_id, session_id)
    acquired = False
    try:
        if not await redis.set(lock_key, "1", nx=True, ex=_LOCK_TTL):
            return
        acquired = True

        key = _key(user_id, session_id)
        stored: dict = {}
        try:
            raw = await redis.get(key)
            if raw:
                data = json.loads(raw)
                if isinstance(data, dict):
                    stored = data
        except Exception:
            stored = {}

        last_key = _msg_key(dropped[-1])
        if stored.get("upto") == last_key:
            return

        # 只送尚未进入摘要的增量片段
        start = 0
        if stored.get("upto"):
            for i, msg in enumerate(dropped):
                if _msg_key(msg) == stored["upto"]:
                    start = i + 1
                    break
        fresh = dropped[start:]
        if len(fresh) < MIN_NEW_MESSAGES:
            return

        conversation = _conversation_text(fresh)
        if not conversation.strip():
            return

        payload = [
            SystemMessage(content=(
                "你是会话压缩器。把【已有摘要】和【新增对话】合并成一段不超过300字的"
                "中文摘要，供后续客服对话使用。必须保留：用户身份与诉求、已确认的事实"
                "（商品ID/订单号/金额/时间）、工具查询得到的结论、未完成事项、用户明确"
                "表达的偏好。不要编造，不要保留寒暄和重复内容。只输出摘要正文。"
            )),
            HumanMessage(content=(
                f"【已有摘要】\n{stored.get('text') or '（无）'}\n\n"
                f"【新增对话】\n{conversation}"
            )),
        ]
        response = await _extract_llm().ainvoke(payload)
        text = _content_text(response.content).strip()[:MAX_SUMMARY_CHARS]
        if not text:
            return

        await redis.set(
            key,
            json.dumps({
                "text": text,
                "upto": last_key,
                "updated_at": time.time(),
            }, ensure_ascii=False),
            ex=SUMMARY_TTL,
        )
        logger.info(
            "会话摘要更新完成 user=%s session=%s covered=%d",
            user_id, session_id, len(fresh),
        )
    except Exception as e:
        logger.warning("会话摘要更新失败(忽略): %s", e)
    finally:
        if acquired:
            try:
                await get_redis().delete(lock_key)
            except Exception:
                pass
