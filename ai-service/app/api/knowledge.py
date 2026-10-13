"""知识库管理 API：FAQ CRUD + 缺口列表 + 重建索引。

管理端通过 product-service AIController 代理调用本路由，实现数据飞轮的
"信号查看 → 补知识 → 索引重建"闭环。

FAQ CRUD 直接操作 ES（mall_faq alias → mall_faq_v3 索引）：
- 列表：_search match_all 分页
- 新增：embed question → index 一条
- 修改：embed question → index 覆盖（ES _id 即 FAQ id）
- 删除：DELETE _doc/{id}
- 重建：从 faq_seed.py 全量重新导入（alias 原子切换，不中断服务）

缺口列表直接查 MySQL faq_gap 表（gap_store.py 写入的信号）。
"""
import asyncio
import json
import logging
from typing import Any

import pymysql
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import settings
from app.core.embeddings import embed_text
from app.core.es_client import (
    FAQ_ALIAS,
    _request,
    bulk_index_faq_v3,
    ensure_faq_index_v3,
    switch_faq_alias,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai/knowledge", tags=["知识库管理"])


# ---- Pydantic 模型 ----

class FAQCreate(BaseModel):
    question: str
    answer: str
    category: str = ""
    tags: list[str] = []
    similar_questions: list[str] = []


class FAQUpdate(FAQCreate):
    pass


class GapStatusUpdate(BaseModel):
    status: int  # 0=待处理 1=已补 2=已忽略


# ---- 缺口列表（MySQL）----

async def _query_gaps(status: int | None, limit: int, offset: int) -> tuple[list[dict], int]:
    """查 faq_gap 表，按 hit_count 降序，返回 (rows, total)。"""
    where = "WHERE 1=1"
    params: list = []
    if status is not None:
        where += " AND status = %s"
        params.append(status)

    def _sync():
        conn = pymysql.connect(
            host=settings.MYSQL_HOST, port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER, password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DB, charset="utf8mb4", connect_timeout=3,
        )
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) AS cnt FROM faq_gap {where}", params)
                total = cur.fetchone()["cnt"]
                cur.execute(
                    f"SELECT id, query, gap_type, detail, hit_count, status, "
                    f"created_at, updated_at FROM faq_gap {where} "
                    f"ORDER BY hit_count DESC, created_at DESC LIMIT %s OFFSET %s",
                    params + [limit, offset],
                )
                rows = cur.fetchall()
                for r in rows:
                    if r.get("detail"):
                        r["detail"] = json.loads(r["detail"])
                    r["created_at"] = r["created_at"].isoformat() if r.get("created_at") else None
                    r["updated_at"] = r["updated_at"].isoformat() if r.get("updated_at") else None
                return rows, total
        finally:
            conn.close()

    return await asyncio.to_thread(_sync)


@router.get("/gaps")
async def list_gaps(
    status: int | None = Query(None, description="0=待处理 1=已补 2=已忽略"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """列出知识库缺口信号（按触发频次降序）。"""
    rows, total = await _query_gaps(status, limit, offset)
    return {"code": 200, "message": "success", "data": rows, "total": total}


@router.put("/gaps/{gap_id}/status")
async def update_gap_status(gap_id: int, body: GapStatusUpdate):
    """更新缺口处理状态（运营补完知识后标记为已补）。"""
    def _sync():
        conn = pymysql.connect(
            host=settings.MYSQL_HOST, port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER, password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DB, charset="utf8mb4", connect_timeout=3,
        )
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE faq_gap SET status = %s WHERE id = %s", (body.status, gap_id))
            conn.commit()
            return cur.rowcount
        finally:
            conn.close()

    affected = await asyncio.to_thread(_sync)
    if not affected:
        raise HTTPException(404, "缺口记录不存在")
    return {"code": 200, "message": "success"}


# ---- FAQ CRUD（ES）----

@router.get("/faqs")
async def list_faqs(
    q: str = Query("", description="搜索关键词"),
    category: str = Query("", description="分类过滤"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """列出 FAQ 条目（ES match_all 或 BM25 搜索）。"""
    body: dict[str, Any] = {"size": limit, "from": offset}
    must = []
    if q:
        must.append({"multi_match": {"query": q, "fields": ["question", "similar_questions"]}})
    if category:
        must.append({"term": {"category": category}})
    body["query"] = {"bool": {"must": must}} if must else {"match_all": {}}

    resp = await _request("POST", f"/{FAQ_ALIAS}/_search", body=body)
    data = resp.json()
    hits = []
    for h in data["hits"]["hits"]:
        s = h["_source"]
        hits.append({
            "id": h["_id"],
            "question": s.get("question", ""),
            "answer": s.get("answer", ""),
            "category": s.get("category", ""),
            "tags": s.get("tags", []),
            "similar_questions": s.get("similar_questions", []),
        })
    return {"code": 200, "message": "success", "data": hits, "total": data["hits"]["total"]["value"]}


@router.post("/faqs")
async def create_faq(body: FAQCreate):
    """新增 FAQ 条目（自动 embed question 写入 ES）。"""
    vector = await embed_text(body.question)
    doc = {
        "question": body.question,
        "answer": body.answer,
        "category": body.category,
        "tags": body.tags,
        "similar_questions": body.similar_questions,
        "version": 1,
        "question_vector": vector,
    }
    resp = await _request("POST", f"/{FAQ_ALIAS}/_doc", body=doc)
    await _request("POST", f"/{FAQ_ALIAS}/_refresh")
    return {"code": 200, "message": "success", "data": {"id": resp.json()["_id"]}}


@router.put("/faqs/{faq_id}")
async def update_faq(faq_id: str, body: FAQUpdate):
    """更新 FAQ 条目（重新 embed question）。"""
    vector = await embed_text(body.question)
    doc = {
        "question": body.question,
        "answer": body.answer,
        "category": body.category,
        "tags": body.tags,
        "similar_questions": body.similar_questions,
        "version": 1,
        "question_vector": vector,
    }
    await _request("PUT", f"/{FAQ_ALIAS}/_doc/{faq_id}", body=doc, ok_codes=(200, 201))
    await _request("POST", f"/{FAQ_ALIAS}/_refresh")
    return {"code": 200, "message": "success"}


@router.delete("/faqs/{faq_id}")
async def delete_faq(faq_id: str):
    """删除 FAQ 条目。"""
    await _request("DELETE", f"/{FAQ_ALIAS}/_doc/{faq_id}", ok_codes=(200, 200))
    await _request("POST", f"/{FAQ_ALIAS}/_refresh")
    return {"code": 200, "message": "success"}


@router.get("/categories")
async def list_categories():
    """列出所有 FAQ 分类（聚合查询）。"""
    body = {"size": 0, "aggs": {"cats": {"terms": {"field": "category", "size": 50}}}}
    resp = await _request("POST", f"/{FAQ_ALIAS}/_search", body=body)
    buckets = resp.json()["aggregations"]["cats"]["buckets"]
    return {"code": 200, "message": "success", "data": [{"name": b["key"], "count": b["doc_count"]} for b in buckets]}


# ---- 重建索引（从 faq_seed 全量重新导入）----

@router.post("/rebuild")
async def rebuild_index():
    """从 faq_seed.py 全量重建 ES 索引（alias 原子切换，不中断服务）。

    耗时操作（300 条 × embedding 调用），前端应显示 loading。
    """
    from scripts.faq_seed import FAQ_ITEMS

    await ensure_faq_index_v3(recreate=True)
    docs = []
    for item in FAQ_ITEMS:
        q = item["question"]
        vector = await embed_text(q)
        docs.append({
            "question": q,
            "answer": item.get("answer", ""),
            "category": item.get("category", ""),
            "tags": item.get("tags", []),
            "similar_questions": item.get("similar_questions", []),
            "version": 1,
            "question_vector": vector,
        })
    count = await bulk_index_faq_v3(docs)
    await switch_faq_alias()
    logger.info("知识库重建完成: %d 条", count)
    return {"code": 200, "message": "success", "data": {"count": count}}
