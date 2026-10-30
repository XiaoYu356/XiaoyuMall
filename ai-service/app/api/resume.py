"""POST /api/v1/ai/v3/resume —— HITL 写操作确认恢复（幂等，语义与 v2 一致）。

- 幂等：Redis `SET resume:{thread_id} NX EX 600`，重复提交 409 已处理；
  Redis 不可用时幂等降级为直通（log warning，不阻断恢复）
- 无 pending interrupt → 400；以 `Command(resume=approved)` 恢复后取
  最后一条非空 AIMessage 作为最终答复返回
- 会话记忆：写入用户决策与助手答复，保证刷新后历史连贯
- 失败路径：清除幂等键后返回 500（与 v2 习惯一致），不重复执行写操作
"""
import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import AIMessage
from langgraph.types import Command
from pydantic import BaseModel

from app.api.chat import _content_text, _pending_interrupts
from app.core.security import get_request_user
from app.memory import get_redis
from app.memory.consolidator import maybe_consolidate
from app.memory.history import add_message

logger = structlog.get_logger(__name__)

router = APIRouter()

# 幂等键 TTL：确认卡片的有效窗口（过期后可重新走一遍流程）
_RESUME_IDEMPOTENT_TTL = 600


class ResumeRequest(BaseModel):
    session_id: str
    approved: bool
    # 身份以 X-User-Id 头 / user_id query 为准；body.user_id 仅作兼容回退
    # （product-service 代理在 body 里携带登录态注入的 user_id）
    user_id: Optional[str] = None


@router.post("/api/v1/ai/v3/resume")
async def resume_write_action(request: Request, body: ResumeRequest):
    """HITL 硬中断恢复：前端确认卡片点击后调用。"""
    # 身份：get_request_user 优先（头/参数），body.user_id 兼容回退
    try:
        user_id = await get_request_user(request)
    except HTTPException:
        if not body.user_id:
            raise
        user_id = body.user_id

    graph = getattr(request.app.state, "ai_graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="AI 服务尚未就绪，请稍后再试")

    thread_id = f"u{user_id}:s{body.session_id}"
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": str(user_id),
            "session_id": body.session_id,
        },
        "recursion_limit": 25,
    }

    # --- 幂等：同一中断只允许恢复一次（重复提交 409，不重复执行写操作） ---
    redis = get_redis()
    resume_key = f"resume:{thread_id}"
    locked = False
    try:
        # NX 抢占成功返回 True；已存在返回 None（视为已处理）
        if not await redis.set(
            resume_key, uuid.uuid4().hex, nx=True, ex=_RESUME_IDEMPOTENT_TTL
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "ALREADY_PROCESSED",
                    "message": "该确认已处理过，请勿重复提交",
                },
            )
        locked = True
    except HTTPException:
        raise
    except Exception as e:
        # Redis 不可用：幂等降级为直通，恢复流程继续
        logger.warning("resume 幂等键写入失败，降级直通", session_id=body.session_id, error=str(e))

    try:
        # --- 校验挂起状态：无 pending interrupt 视为无效恢复 ---
        state = await graph.aget_state(config)
        if not _pending_interrupts(state):
            if locked:
                await redis.delete(resume_key)
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "NO_PENDING_INTERRUPT",
                    "message": "没有待确认的操作或该操作已处理",
                },
            )
        result = await graph.ainvoke(Command(resume=body.approved), config)
    except HTTPException:
        raise
    except Exception as e:
        # 失败路径：清除幂等键，允许用户重试
        if locked:
            try:
                await redis.delete(resume_key)
            except Exception:
                pass
        logger.exception("恢复写操作失败", session_id=body.session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"恢复操作失败: {e}")

    # 取恢复后 Agent 的最终答复（最后一条非空 AI 消息）
    text = ""
    for msg in reversed(result.get("messages", []) or []):
        if isinstance(msg, AIMessage):
            text = _content_text(msg.content)
            if text:
                break

    # 会话记忆：用户决策 + 助手答复（最佳努力）
    try:
        await add_message(
            str(user_id), body.session_id, "user",
            f"用户选择了[{'同意' if body.approved else '拒绝'}]售后操作",
        )
        if text:
            await add_message(str(user_id), body.session_id, "assistant", text)
        await maybe_consolidate(str(user_id), body.session_id)
    except Exception as e:
        logger.warning("写入会话记忆失败(忽略)", error=str(e))

    return {
        "success": True,
        "data": {
            "approved": body.approved,
            "message": text or ("操作已完成。" if body.approved else "已取消。"),
        },
    }
