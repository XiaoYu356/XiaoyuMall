"""AI 写操作审计：落库 mall_order.ai_action_audit。

设计要点：
- 最佳努力：审计失败只记日志，绝不阻断售后主流程
- pymysql 为同步驱动，用 asyncio.to_thread 避免阻塞事件循环
- 每次调用新建短连接：写操作低频（仅 HITL 确认后的真实执行），
  省掉连接池保活的复杂度
"""
import asyncio
import json
import logging

import pymysql

from app.core.config import settings

logger = logging.getLogger(__name__)

_INSERT_SQL = (
    "INSERT INTO ai_action_audit "
    "(user_id, session_id, tool_name, order_no, params, result, detail) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
)


def _insert_sync(row: tuple) -> None:
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


async def write_audit(
    *,
    user_id: str,
    session_id: str | None,
    tool_name: str,
    order_no: str | None = None,
    params: dict | None = None,
    result: str,
    detail: str | None = None,
) -> None:
    """写一条审计记录。result 取值：success / rejected / failed。"""
    row = (
        str(user_id),
        session_id or "",
        tool_name,
        order_no,
        json.dumps(params or {}, ensure_ascii=False),
        result,
        (detail or "")[:900],
    )
    try:
        await asyncio.to_thread(_insert_sync, row)
    except Exception as e:
        logger.warning("审计落库失败(忽略) tool=%s order=%s: %s", tool_name, order_no, e)
