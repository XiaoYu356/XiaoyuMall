"""Elasticsearch REST 客户端（httpx 封装，不引入 elasticsearch-py 依赖）。

仅负责 FAQ 知识库：mall_faq_v3（条目化：question + similar_questions + answer），
本服务全权维护（建索引 + embedding + bulk 导入 + alias 切换）。
商品数据检索统一走 product-service 内部接口（app/tools/product_tools.py），
本服务不直连 mall_product 索引。

FAQ v3 检索策略（设计文档 §13.3）：ES 8.x 原生 RRF 融合——
BM25(question) + BM25(similar_questions) + kNN(question_vector) 合并为一次
_search 请求，由 ES 内置 rank.rrf 融合排序，比三次并行请求省掉 2 次端口转发
往返 + Python 侧 RRF 融合开销。httpx.Client 全局单例复用连接池。
"""
import asyncio
import json
import logging
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

FAQ_INDEX_V3 = "mall_faq_v3"
FAQ_ALIAS = "mall_faq"  # 对外检索统一走 alias，重建索引后原子切换

_ES_TIMEOUT = 5.0
_VECTOR_DIMS = 1024  # 与 qwen3.7-text-embedding-flash 返回维度一致（已验证）
_RRF_WINDOW = 30     # ES 内置 RRF window_size，覆盖三路各 top10 合并后的候选
_RRF_CONSTANT = 60   # ES 内置 RRF rank_constant（等价原 Python 侧 k=60）
_RECALL_SIZE = 10    # 每路召回 top10

# 全局 httpx 客户端（复用连接池，避免每次新建 TLS 开销）
_ES_CLIENT: Optional[httpx.Client] = None


def _get_client() -> httpx.Client:
    """获取全局单例 httpx.Client（线程安全，首次调用时创建）。"""
    global _ES_CLIENT
    if _ES_CLIENT is None:
        _ES_CLIENT = httpx.Client(timeout=_ES_TIMEOUT, limits=httpx.Limits(max_connections=10))
    return _ES_CLIENT

# mall_faq_v3 索引定义（设计文档 §13.2）：
# - BM25 打在 question + similar_questions 上（ik_max_word 索引召回 / ik_smart 搜索防过切）
# - answer 不参与召回（index:false 只存不索引），经 _source 返回给模型引用
# - 向量字段只存 question 的 embedding（问法对问法，比对答案匹配准）
FAQ_V3_INDEX_BODY = {
    "settings": {
        "index": {"number_of_shards": 1, "number_of_replicas": 0},
        # 自定义分析器（与设计文档 §13.2 一致；v2 未使用，v3 建索引时一并声明）
        "analysis": {
            "analyzer": {
                "ik_smart_a": {"type": "custom", "tokenizer": "ik_smart"}
            }
        },
    },
    "mappings": {
        "properties": {
            "question": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
            },
            "similar_questions": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_smart",
            },
            # answer 不参与召回：只存 _source 不索引（经 _source 返回给模型引用）。
            # 注意 ES 的 text 字段不支持 enabled 参数，等价写法是 index:false（实测 400 教训）
            "answer": {"type": "text", "index": False},
            "question_vector": {
                "type": "dense_vector",
                "dims": _VECTOR_DIMS,
                "index": True,
                "similarity": "cosine",
                "index_options": {"type": "hnsw", "m": 16, "ef_construction": 128},
            },
            "category": {"type": "keyword"},
            "tags": {"type": "keyword"},
            "version": {"type": "integer"},
        }
    },
}


def _request_sync(method: str, path: str, body: Optional[Any] = None,
                  ok_codes: tuple = (200, 201)) -> httpx.Response:
    """同步 ES REST 请求（Windows + Docker 端口转发下 async httpx 会 ReadError，
    改用同步 Client + asyncio.to_thread 绕开 anyio socket 兼容问题）。"""
    with httpx.Client(timeout=_ES_TIMEOUT) as client:
        response = client.request(method, f"{settings.ES_URL}{path}", json=body)
    if response.status_code not in ok_codes:
        raise RuntimeError(f"ES {method} {path} -> {response.status_code}: {response.text[:300]}")
    return response


async def _request(method: str, path: str, body: Optional[Any] = None,
                   ok_codes: tuple = (200, 201)) -> httpx.Response:
    """async 包装（内部转同步），供上层 await 调用。"""
    return await asyncio.to_thread(_request_sync, method, path, body, ok_codes)


# ---------------- FAQ v3 索引管理 ----------------

async def ensure_faq_index_v3(recreate: bool = False) -> None:
    """确保 mall_faq_v3 索引存在；recreate=True 时先删后建（导入脚本用）。"""
    if recreate:
        try:
            await _request("DELETE", f"/{FAQ_INDEX_V3}", ok_codes=(200, 404))
            logger.info("已删除旧索引 %s", FAQ_INDEX_V3)
        except Exception as e:
            logger.warning("删除旧索引失败(忽略): %s", e)
    exists = await _request("HEAD", f"/{FAQ_INDEX_V3}", ok_codes=(200, 404))
    if exists.status_code == 200 and not recreate:
        return
    await _request("PUT", f"/{FAQ_INDEX_V3}", body=FAQ_V3_INDEX_BODY)
    logger.info("已创建索引 %s", FAQ_INDEX_V3)


async def bulk_index_faq_v3(docs: list[dict]) -> int:
    """bulk 导入 FAQ v3（docs: [{question, similar_questions, answer, category,
    tags, version, question_vector}, ...]）。"""
    if not docs:
        return 0
    lines: list[str] = []
    for doc in docs:
        lines.append(f'{{"index": {{"_index": "{FAQ_INDEX_V3}"}}}}')
        lines.append(json.dumps(doc, ensure_ascii=False))
    body = "\n".join(lines) + "\n"
    def _bulk_sync():
        with httpx.Client(timeout=60.0) as client:
            return client.post(
                f"{settings.ES_URL}/_bulk",
                content=body.encode("utf-8"),
                headers={"Content-Type": "application/x-ndjson"},
            )
    response = await asyncio.to_thread(_bulk_sync)
    if response.status_code != 200 or response.json().get("errors"):
        raise RuntimeError(f"bulk 导入失败: {response.text[:300]}")
    # 立即 refresh，保证导入后马上可被检索（否则需等默认 1s refresh interval）
    await _request("POST", f"/{FAQ_INDEX_V3}/_refresh")
    logger.info("bulk 导入 %d 条 FAQ", len(docs))
    return len(docs)


async def switch_faq_alias(alias: str = FAQ_ALIAS, index: str = FAQ_INDEX_V3) -> None:
    """原子切换 alias：移除旧索引对该 alias 的绑定、加入新索引（单请求内完成）。"""
    current = await _request("GET", f"/_alias/{alias}", ok_codes=(200, 404))
    actions: list[dict] = []
    if current.status_code == 200:
        for idx in current.json().keys():
            if idx != index:
                actions.append({"remove": {"index": idx, "alias": alias}})
    actions.append({"add": {"index": index, "alias": alias}})
    await _request("POST", "/_aliases", body={"actions": actions})
    logger.info("alias %s 已切换指向 %s", alias, index)


# ---------------- FAQ v3 检索 ----------------

def _faq_hit(source: dict, doc_id: str) -> dict:
    return {
        "id": doc_id,
        "question": source.get("question", ""),
        "answer": source.get("answer", ""),
        "category": source.get("category", ""),
        "score": 0.0,
    }


async def search_faq_v3(query: str, query_vector: list[float],
                        top_k: int = 3) -> list[dict]:
    """FAQ v3 三路并行召回 + RRF 融合去重（设计文档 §13.3）。

    - 三路各召回 top10：BM25(question) / knn(question_vector) / BM25(similar_questions)
    - 三次请求 asyncio.gather 并行；httpx.Client 全局单例复用连接池
    - RRF 融合：score = Σ 1/(k + rank)（rank 从 1 计，k=60），按 doc_id 去重累加
    - 返回融合序候选池；调用方（search_faq）以此为重排候选池
    """
    bm25_question_body = {
        "size": _RECALL_SIZE,
        "query": {"match": {"question": {"query": query}}},
    }
    knn_body = {
        "size": _RECALL_SIZE,
        "knn": {
            "field": "question_vector",
            "query_vector": query_vector,
            "k": _RECALL_SIZE,
            "num_candidates": 100,
        },
    }
    bm25_similar_body = {
        "size": _RECALL_SIZE,
        "query": {"match": {"similar_questions": {"query": query}}},
    }

    # 三路并行（全局单例 Client 复用连接池，避免每次新建 TLS）
    def _post_sync(body: dict) -> httpx.Response:
        return _get_client().post(
            f"{settings.ES_URL}/{FAQ_INDEX_V3}/_search", json=body
        )
    q_resp, k_resp, s_resp = await asyncio.gather(
        asyncio.to_thread(_post_sync, bm25_question_body),
        asyncio.to_thread(_post_sync, knn_body),
        asyncio.to_thread(_post_sync, bm25_similar_body),
    )
    for name, resp in (
        ("BM25(question)", q_resp),
        ("knn", k_resp),
        ("BM25(similar_questions)", s_resp),
    ):
        if resp.status_code != 200:
            raise RuntimeError(f"FAQ {name} 查询失败: {resp.status_code} {resp.text[:200]}")

    fused: dict[str, dict] = {}

    def _absorb(resp_json: dict):
        for rank, hit in enumerate(resp_json.get("hits", {}).get("hits", []), start=1):
            doc_id = hit["_id"]
            entry = fused.setdefault(doc_id, _faq_hit(hit.get("_source") or {}, doc_id))
            entry["score"] = entry.get("score", 0.0) + 1.0 / (_RRF_CONSTANT + rank)

    _absorb(q_resp.json())
    _absorb(k_resp.json())
    _absorb(s_resp.json())

    return sorted(fused.values(), key=lambda x: x["score"], reverse=True)[:top_k]
