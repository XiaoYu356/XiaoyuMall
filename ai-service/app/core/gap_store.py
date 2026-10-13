"""FAQ 检索缺口信号持久化：落库 mall_order.faq_gap。

数据飞轮的信号采集层：检索时 all_killed / gray_killed 的 query 写入 MySQL，
运营在管理端查看缺口列表 → 补知识 → 状态置为已补 → 闭环。

设计要点（与 audit.py 一致）：
- 最佳努力：写入失败只记日志，绝不阻断检索主流程
- pymysql 同步驱动，用 asyncio.to_thread 避免阻塞事件循环
- 短连接：gap 写入低频，省连接池保活复杂度
"""
import asyncio
import json
import logging

import pymysql

from app.core.config import settings

logger = logging.getLogger(__name__)

_UPSERT_SQL = (
    "INSERT INTO faq_gap(query, gap_type, detail) VALUES(%s, %s, %s) "
    "ON DUPLICATE KEY UPDATE hit_count = hit_count + 1, updated_at = NOW()"
)


def _upsert_sync(query: str, gap_type: int, detail: dict) -> None:
    conn = pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DB,
        charset="utf8mb4",
        connect_timeout=3,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(_UPSERT_SQL, (query[:255], gap_type, json.dumps(detail, ensure_ascii=False)))
        conn.commit()
    finally:
        conn.close()


async def record_gap(query: str, gap_type: int, detail: dict) -> None:
    """记录一条缺口信号。gap_type: 1=all_killed 2=gray_killed。"""
    try:
        await asyncio.to_thread(_upsert_sync, query, gap_type, detail)
    except Exception as e:
        logger.warning("缺口信号落库失败(忽略): %s", e)
