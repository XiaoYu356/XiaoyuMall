"""本地 bge-m3 向量化封装（FlagEmbedding，GPU 优先）。

- 模型 BAAI/bge-m3，多语言，输出 1024 维
  （与 mall_faq_v3.question_vector 的 dims 一致，无需改 ES mapping）
- 模型首次调用时自动下载约 2GB 到 ~/.cache/huggingface
- 全局单例：进程生命周期只 load 一次，避免重复加载拖慢启动
- 同步函数（FlagEmbedding 非 async），用 asyncio.to_thread 避免阻塞事件循环
- fail-open：本地模型加载失败时回退 httpx 调云端（如果 OPENAI_API_KEY 还有额度）
"""
import asyncio
import logging
import threading
from collections import OrderedDict
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---- 本地模型 ----
# ModelScope 国内镜像下载路径（huggingface.co 被墙）
_LOCAL_EMBED_PATH = r"C:\Users\ASUS\.cache\modelscope\models\BAAI--bge-m3\snapshots\master"
_LOCAL_EMBED_DIMS = 1024

# ---- 云端回退 ----
_CLOUD_EMBED_MODEL = "qwen3.7-text-embedding-flash"
_EMBED_TIMEOUT = 10.0
_BATCH_SIZE = 32  # 本地模型一次可以推更多

# ---- embed 缓存 ----
# 单 query 向量化是纯函数（bge-m3 无随机性），LRU 缓存省掉重复 query 的 embed 开销
# 键是 query 字符串，值是 1024 维 list；maxlen=128 覆盖会话内高频重复问法
_EMBED_CACHE: "OrderedDict[str, list[float]]" = OrderedDict()
_EMBED_CACHE_MAXLEN = 128
_EMBED_CACHE_LOCK = threading.Lock()

# 全局单例 + 可重入锁：asyncio.to_thread 多线程并发加载时保证只加载一次；
# RLock（非 Lock）使同线程内"推理持锁 → 懒加载再取锁"不死于重入死锁，
# 同时推理全程持锁串行化——PyTorch CUDA context 不支持多线程并发调用
# （评测侧已实证：并发推理进程直接崩溃），必须串行
_encoder = None
_encoder_lock = threading.RLock()


def _load_local_encoder():
    """懒加载本地 bge-m3，返回 FlagEmbedding.BGEM3FlagModel。

    用 threading.Lock 保证多线程并发时只加载一次，其他线程等加载完再返回。
    CUDA 可用时用 FP16（自动上 GPU），否则 FP32 跑 CPU。
    """
    global _encoder
    with _encoder_lock:
        if _encoder is not None:
            return _encoder
        try:
            import torch
            from FlagEmbedding import BGEM3FlagModel
            use_fp16 = torch.cuda.is_available()
            logger.info(
                "正在加载本地 bge-m3 embedding 模型（首次可能需下载，fp16=%s）...", use_fp16,
            )
            _encoder = BGEM3FlagModel(_LOCAL_EMBED_PATH, use_fp16=use_fp16)
            logger.info("本地 bge-m3 加载完成 fp16=%s", use_fp16)
        except Exception as e:
            logger.warning("本地 bge-m3 加载失败: %s，将回退云端", e)
            _encoder = None
    return _encoder


def _embed_local_sync(texts: list[str]) -> list[list[float]]:
    """本地 bge-m3 同步向量化（FlagEmbedding 的 encode 返回 np.ndarray）。

    推理全程持锁：与模型加载互斥，且串行化 CUDA 调用（多线程并发会崩进程）。
    """
    with _encoder_lock:
        enc = _load_local_encoder()
        if enc is None:
            raise RuntimeError("本地 embedding 模型不可用")
        # bge-m3 返回 [batch, dim] 的 ndarray
        vectors = enc.encode(texts, batch_size=_BATCH_SIZE)["dense_vecs"]
    return vectors.tolist()


async def _embed_cloud(texts: list[str]) -> list[list[float]]:
    """云端回退（DashScope / 兼容端点）。"""
    vectors: list[list[float]] = []
    for i in range(0, len(texts), 10):
        payload: dict[str, Any] = {"model": _CLOUD_EMBED_MODEL, "input": texts[i:i + 10]}
        async with httpx.AsyncClient(timeout=_EMBED_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.OPENAI_API_BASE}/embeddings",
                json=payload,
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            )
        if resp.status_code != 200:
            raise RuntimeError(f"embedding 调用失败: HTTP {resp.status_code}")
        vectors.extend(d["embedding"] for d in resp.json()["data"])
    return vectors


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量向量化：本地 bge-m3 优先，失败回退云端。"""
    try:
        return await asyncio.to_thread(_embed_local_sync, texts)
    except Exception as e:
        logger.warning("本地 embedding 失败(回退云端): %s", e)
        if settings.OPENAI_API_KEY:
            return await _embed_cloud(texts)
        raise


async def embed_text(text: str) -> list[float]:
    """单文本向量化（带 LRU 缓存，重复 query 零开销）。"""
    # 命中缓存 → O(1) 返回
    with _EMBED_CACHE_LOCK:
        if text in _EMBED_CACHE:
            _EMBED_CACHE.move_to_end(text)
            return _EMBED_CACHE[text]
    # 未命中 → 走完整 embedding 管线
    vector = (await embed_texts([text]))[0]
    with _EMBED_CACHE_LOCK:
        _EMBED_CACHE[text] = vector
        _EMBED_CACHE.move_to_end(text)
        while len(_EMBED_CACHE) > _EMBED_CACHE_MAXLEN:
            _EMBED_CACHE.popitem(last=False)
    return vector
