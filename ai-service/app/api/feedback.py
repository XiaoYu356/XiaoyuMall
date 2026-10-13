"""POST /api/v1/ai/v3/feedback —— 用户 👍/👎 反馈落库 ai_chat_feedback（评估闭环数据源）。

落库模式与 app/core/audit.py 一致：pymysql 同步驱动 + asyncio.to_thread +
best-effort（失败不抛错，返回 success=false，HTTP 200）。
request_id 可关联该次对话的 Langfuse trace，用于答案修正与 golden 数据集回流。
"""
import asyncio
import logging

import pymysql
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import get_request_user

logger = logging.getLogger(__name__)

router = APIRouter()

_INSERT_SQL = (
    "INSERT INTO ai_chat_feedback "
    "(request_id, user_id, session_id, rating, comment) "
    "VALUES (%s, %s, %s, %s, %s)"
)


def _insert_sync(row: tuple) -> None:
    """同步写一条反馈（每次调用新建短连接，写操作低频，省掉连接池保活）。"""
    conn = pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DB,
        charset="utf8mb4",
        connect_timeout=5,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(_INSERT_SQL, row)
        conn.commit()
    finally:
        conn.close()


class FeedbackRequest(BaseModel):
    request_id: str
    session_id: str
    rating: int = Field(ge=0, le=1, description="1=赞 0=贬")
    comment: str | None = Field(default=None, max_length=500)


@router.post("/api/v1/ai/v3/feedback")
async def submit_feedback(
    body: FeedbackRequest,
    user_id: str = Depends(get_request_user),
):
    """提交反馈：成功 {"success": true}；落库失败 best-effort 返回 {"success": false}（HTTP 200）。"""
    # 表中 user_id 为 BIGINT：非数字身份兜底为 0（不阻断反馈提交）
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        uid = 0

    row = (
        body.request_id[:64],
        uid,
        body.session_id[:64],
        body.rating,
        body.comment,
    )
    try:
        await asyncio.to_thread(_insert_sync, row)
    except Exception as e:
        logger.warning("反馈落库失败(忽略) request_id=%s: %s", body.request_id, e)
        return {"success": False, "message": f"反馈提交失败: {e}"}
    return {"success": True}
