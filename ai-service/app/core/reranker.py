"""本地 bge-reranker-v2-m3 重排封装（FlagEmbedding，GPU 优先）。

- 模型 BAAI/bge-reranker-v2-m3，cross-encoder，输出绝对相关性分数（raw logits，非 0~1 概率）
- 分数有绝对语义：同构调用（单 query + 固定候选池）下可跨请求比较
  —— 这是阈值分级（app/core/config.py 的 T_HIGH/T_MID/T_LOW）的前提
- 全局单例：进程生命周期只 load 一次
- 同步函数用 asyncio.to_thread 避免阻塞事件循环
- fail-open：本地模型加载失败时返回 None，由调用方（search_faq）退回 RRF 序
"""
import asyncio
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_LOCAL_RERANK_PATH = r"C:\Users\ASUS\.cache\modelscope\models\BAAI--bge-reranker-v2-m3\snapshots\master"

# 全局单例 + 可重入锁（同 embeddings.py，解决 asyncio.to_thread 多线程竞态）；
# RLock 使同线程内"推理持锁 → 懒加载再取锁"不死于重入死锁，推理全程持锁
# 串行化——PyTorch CUDA context 不支持多线程并发调用（评测侧已实证会崩进程）
_cross_encoder = None
_reranker_lock = threading.RLock()


def _load_local_reranker():
    """懒加载本地 bge-reranker-v2-m3，线程锁保证只加载一次。

    CUDA 可用时用 FP16（自动上 GPU），否则 FP32 跑 CPU。
    """
    global _cross_encoder
    with _reranker_lock:
        if _cross_encoder is not None:
            return _cross_encoder
        try:
            import torch
            use_fp16 = torch.cuda.is_available()
            try:
                from FlagEmbedding import FlagReranker
                logger.info("正在加载本地 bge-reranker-v2-m3（FlagReranker，fp16=%s）...", use_fp16)
                _cross_encoder = FlagReranker(_LOCAL_RERANK_PATH, use_fp16=use_fp16)
            except ImportError:
                from FlagEmbedding import FlagModel
                logger.info("正在加载本地 bge-reranker-v2-m3（FlagModel 兼容模式，fp16=%s）...", use_fp16)
                _cross_encoder = ("FlagModel", FlagModel(_LOCAL_RERANK_PATH, use_fp16=use_fp16))
            logger.info("本地 bge-reranker-v2-m3 加载完成 fp16=%s", use_fp16)
        except Exception as e:
            logger.warning("本地 bge-reranker-v2-m3 加载失败: %s", e)
            _cross_encoder = None
    return _cross_encoder


def _rerank_local_sync(query: str, docs: list[str], top_n: int) -> list[tuple[int, float]]:
    """本地 cross-encoder 重排，返回 [(下标, score)] 按 score 降序。

    推理全程持锁：与模型加载互斥，且串行化 CUDA 调用（多线程并发会崩进程）。
    """
    with _reranker_lock:
        model = _load_local_reranker()
        if model is None:
            raise RuntimeError("本地 reranker 模型不可用")

        if isinstance(model, tuple) and model[0] == "FlagModel":
            # FlagModel 兼容：用 FlagModel.encode 的 pairwise
            # bge-reranker-v2-m3 作为 cross-encoder 时，输入格式是 query + doc
            fm = model[1]
            pairs = [(query, doc) for doc in docs]
            scores = fm.encode(pairs, batch_size=8)
            scores = scores.tolist() if hasattr(scores, "tolist") else list(scores)
        else:
            # FlagReranker 原生接口
            pairs = [[query, doc] for doc in docs]
            scores = model.compute_score(pairs)
            scores = scores if isinstance(scores, list) else scores.tolist()

    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return ranked[:top_n]


# ---- 云端回退（保留，本地不可用时生效）----
_DASHSCOPE_RERANK_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1"
_INSTRUCT = "Retrieve semantically similar text."


async def _rerank_cloud(query: str, docs: list[str], top_n: int) -> Optional[list[tuple[int, float]]]:
    """云端重排（DashScope，有 key 才生效）。"""
    import httpx
    from app.core.config import settings

    if not settings.RERANK_API_KEY and not settings.OPENAI_API_KEY:
        return None
    api_key = settings.RERANK_API_KEY or settings.OPENAI_API_KEY
    payload = {
        "model": settings.RERANK_MODEL,
        "input": {"query": query, "documents": docs},
        "parameters": {"top_n": min(top_n, len(docs)), "instruct": _INSTRUCT},
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{_DASHSCOPE_RERANK_ENDPOINT}/services/rerank/text-rerank/text-rerank",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
        if resp.status_code != 200:
            return None
        results = (resp.json().get("output") or {}).get("results") or []
        return sorted(
            [(item["index"], float(item["relevance_score"])) for item in results],
            key=lambda x: x[1], reverse=True,
        )[:top_n]
    except Exception:
        return None


async def rerank(query: str, docs: list[str], top_n: int) -> Optional[list[tuple[int, float]]]:
    """重排：本地 bge-reranker-v2-m3 优先，失败回退云端，最终失败返回 None。"""
    if not docs:
        return []
    try:
        return await asyncio.to_thread(_rerank_local_sync, query, docs, top_n)
    except Exception as e:
        logger.warning("本地 rerank 失败(回退云端): %s", e)
        result = await _rerank_cloud(query, docs, top_n)
        if result is not None:
            return result
        logger.warning("rerank 全部失败(返回 None，调用方 fail-open)")
        return None


def build_rerank_doc(hit: dict) -> str:
    """构造重排输入文档（本地/云端通用）。"""
    return f"{hit.get('question', '')}\n{hit.get('answer', '')[:300]}".strip()
