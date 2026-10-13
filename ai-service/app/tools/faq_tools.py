"""知识域工具：search_faq（混合检索 + cross-encoder 精排 + 置信度分级）。

检索管线：三路召回（BM25(question) / kNN / BM25(similar_questions)）→ RRF 融合
去重 → 候选池 top10 → bge-reranker-v2-m3 cross-encoder 精排 → top3 + 阈值分级。

v3.1 改造（替代原 CRAG LLM 判级，依据检索层评测实证）：
- RRF 分是 rank 的函数、无绝对语义（域外 query 也能拿 0.045+ 共识分），只能排序
  不能判相关；cross-encoder 的分数（raw logits，非 0~1 概率）具有绝对相关性语义，
  在评测集上按正/负样本分数分布校准出三档阈值
  （scripts/eval/calibrate_rerank_thresholds.py）：
    score >= T_HIGH            高置信：正常引用（confidence=high）
    T_MID <= score < T_HIGH    中置信：保留并标注（confidence=mid），提示谨慎表述
    T_LOW  <= score < T_MID    低置信：剔除（灰区条目打日志供运营观察）
    score <  T_LOW             剔除（绝对无关区）
  在线动作上 T_LOW/T_MID 均为剔除线；T_LOW 的独立价值在校准可观测
  （负样本中位线）与后续级联演进（low 灰区可喂 LLM 二次判级）的触发线
- 全部候选被剔除时返回空 refs，agent 走"如实告知"兜底（域外误召回的结构化拦截）
- rerank 失败/超时 fail-open 退回 RRF top3 原序（可用性优先，重排是增强层）

成功返回 JSON 字符串 {"refs":[...]}，SSE 层据此发 citation 事件；
检索异常返回可读错误文本（不抛）。
"""
import json
import logging
import time

from langchain_core.tools import tool

from app.core.config import settings
from app.core.embeddings import embed_text
from app.core.es_client import search_faq_v3
from app.core.gap_store import record_gap
from app.core.reranker import build_rerank_doc, rerank
from app.tools.base import timed_call

logger = logging.getLogger(__name__)


async def _build_refs(
    query: str, candidates: list[dict], ranked: list[tuple[int, float]]
) -> tuple[list[dict], int]:
    """按重排分对候选做置信度分级，返回 (保留条目, 缺口等级)。

    缺口等级按 top1 最高分所在区间判定（按 query 粒度，不按候选逐条）：
    0=top1≥T_HIGH 知识够用，不产生信号；
    1=top1<T_MID 全缺口，知识库无相关知识，高优先级补录；
    2=T_MID≤top1<T_HIGH 弱覆盖，有参考但置信不足，低优先级复核改写。
    """
    refs: list[dict] = []
    top1_score = ranked[0][1] if ranked else float("-inf")

    for idx, score in ranked:
        h = candidates[idx]
        if score < settings.RERANK_T_MID:
            continue
        refs.append({
            "no": len(refs) + 1,
            "question": h.get("question", ""),
            "answer": h.get("answer", ""),
            "score": round(score, 4),
            "confidence": "high" if score >= settings.RERANK_T_HIGH else "mid",
            "category": h.get("category", ""),
        })

    if top1_score >= settings.RERANK_T_HIGH:
        gap_level = 0
    elif top1_score >= settings.RERANK_T_MID:
        gap_level = 2
    else:
        gap_level = 1
    return refs, gap_level


@tool
async def search_faq(query: str) -> str:
    """检索商城平台政策/规则/费用/流程类知识（售后、退款、发货、优惠券规则、账号问题等）。
    查商品、订单、优惠券实时数据不要用本工具。工具内置重排与置信度分级：refs 为空表示
    知识库无相关内容，可换关键词重查（最多 2 次），仍为空则如实告知用户暂无相关说明。

    Args:
        query: 用户问题的提炼版（保留关键数字与商品词，如"7天无理由退货条件"）
    """

    async def _run() -> str:
        t0 = time.perf_counter()
        vector = await embed_text(query)
        t1 = time.perf_counter()
        # 候选池：RRF 融合去重后取 top10（重排需要裁剪空间，直接 top3 无精排价值）
        candidates = await search_faq_v3(query, vector, top_k=settings.RERANK_CANDIDATES)
        t2 = time.perf_counter()
        if not candidates:
            logger.info(
                "search_faq 空召回(query=%s embed=%.0fms es=%.0fms)",
                query[:50], (t1 - t0) * 1000, (t2 - t1) * 1000,
            )
            return json.dumps({"refs": []}, ensure_ascii=False)

        ranked = await rerank(
            query, [build_rerank_doc(h) for h in candidates], top_n=3,
        )
        t3 = time.perf_counter()
        rerank_ms = (t3 - t2) * 1000
        if ranked is None:
            # fail-open：重排不可用，退回 RRF 融合序 top3，不带置信度标注
            logger.warning(
                "search_faq 重排失败退回RRF(query=%s embed=%.0fms es=%.0fms rerank=%.0fms)",
                query[:50], (t1 - t0) * 1000, (t2 - t1) * 1000, rerank_ms,
            )
            refs = [
                {
                    "no": i + 1,
                    "question": h.get("question", ""),
                    "answer": h.get("answer", ""),
                    "score": round(h.get("score", 0.0), 4),
                    "category": h.get("category", ""),
                }
                for i, h in enumerate(candidates[:3])
            ]
            return json.dumps({"refs": refs}, ensure_ascii=False)

        refs, gap_level = await _build_refs(query, candidates, ranked)
        logger.info(
            "search_faq 耗时(query=%s embed=%.0fms es=%.0fms rerank=%.0fms "
            "候选=%d refs=%d top1=%.2f)",
            query[:50], (t1 - t0) * 1000, (t2 - t1) * 1000, rerank_ms,
            len(candidates), len(refs), ranked[0][1] if ranked else 0.0,
        )
        if gap_level:
            top1_score = round(ranked[0][1], 4) if ranked else 0.0
            top1_q = candidates[ranked[0][0]].get("question", "")[:80] if ranked else ""
            logger.info(
                "search_faq 缺口信号(query=%s gap_type=%d top1_score=%.4f)",
                query[:50], gap_level, top1_score,
            )
            await record_gap(query, gap_level, {
                "top1_score": top1_score,
                "top1_candidate": top1_q,
            })
        return json.dumps({"refs": refs}, ensure_ascii=False)

    return await timed_call("search_faq", _run, service="知识库服务")
