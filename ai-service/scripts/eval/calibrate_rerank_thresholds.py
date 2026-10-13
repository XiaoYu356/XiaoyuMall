"""重排置信度阈值校准 runner（v3.1，检索层专项）。

目的：cross-encoder 的分数（raw logits，非 0~1 概率）具有绝对相关性语义，但阈值不能拍
脑袋 —— 在检索评测集上按正/负样本分数分布校准出三档置信度阈值，并回验分级
对域内指标与域外拦截的影响。校准产出的阈值回填 app/core/config.py。

口径（与线上 search_faq 完全同构，阈值与口径强耦合）：
    embed_text → search_faq_v3(top_k=RERANK_CANDIDATES) → rerank(build_rerank_doc)
    （重排 top_n 传候选池全量，拿全部候选分数；top_n 只截返回条数不影响分数）

样本定义：
    正样本：covered/multi 中命中 gold 的候选分数（每 query 取 gold 命中候选的最高分，
            即"该 query 的最佳相关条目得分"）
    负样本：robust（域外）每 query 候选池的最高分（最坏情况 = 重排后会排第一的条目）

阈值推导规则（可解释、可复现）：
    T_HIGH = neg_max 的 P99  —— 高置信误召回 ≤1%
    T_MID  = neg_max 的 P95  —— 域外误进（refs 非空）≤5%
    T_LOW  = neg_max 的 P50  —— 半数域外落在绝对无关区
    回验：正样本 per-query 存活率（≥1 条 gold 候选 ≥T_MID）应 ≥95%；
    若与误进约束冲突（分布重叠），报告显式给出冲突告警与 EER 参考。

对照指标（同一评测集三种口径）：
    rrf_top3        ：RRF 融合序直接取 top3（改造前基线，无任何过滤）
    rerank_top3     ：重排序取 top3（纯精排收益，不过阈值）
    rerank_graded   ：重排 + T_MID 分级（线上实际行为）

运行（cwd=ai-service）：
    .venv\\Scripts\\python.exe -m scripts.eval.calibrate_rerank_thresholds [--limit N]
报告写入 scripts/eval/reports/calibration_report_{ts}.json。
"""
import argparse
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.core.embeddings import embed_text
from app.core.es_client import search_faq_v3
from app.core.reranker import build_rerank_doc, rerank

HERE = Path(__file__).parent
DATASET = HERE / "retrieval_set.jsonl"
REPORTS = HERE / "reports"
CONCURRENCY = 1  # 本地 GPU 推理非线程安全，串行跑
QUANTILES = (0.05, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)


def _load() -> list[dict]:
    rows = []
    with DATASET.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _quantile(xs: list[float], q: float) -> float:
    """线性插值分位数（xs 无序输入，内部排序）。"""
    if not xs:
        return 0.0
    s = sorted(xs)
    pos = (len(s) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def _percentile_table(xs: list[float]) -> dict:
    return {
        "n": len(xs),
        "mean": round(sum(xs) / len(xs), 4) if xs else 0.0,
        **{f"p{int(q * 100)}": round(_quantile(xs, q), 4) for q in QUANTILES},
    }


def _metrics(refs: list[dict], gold: set[str]) -> dict:
    """与 run_retrieval_eval 同口径：hit@1 / recall@3 / MRR（refs 需含 question）。"""
    hits3 = sum(1 for r in refs[:3] if r["question"] in gold)
    rank = next((i for i, r in enumerate(refs, 1) if r["question"] in gold), 0)
    return {
        "hit1": 1 if rank == 1 else 0,
        "recall": hits3 / len(gold) if gold else 0.0,
        "mrr": 1.0 / rank if rank else 0.0,
    }


def _agg(metrics: list[dict]) -> dict:
    n = len(metrics)
    if not n:
        return {"n": 0}
    return {
        "n": n,
        "hit@1": round(sum(m["hit1"] for m in metrics) / n, 3),
        "recall@3": round(sum(m["recall"] for m in metrics) / n, 3),
        "mrr": round(sum(m["mrr"] for m in metrics) / n, 3),
    }


async def _eval_one(row: dict, sem: asyncio.Semaphore) -> dict:
    """单条评测：候选池全量重排分数 + 三种口径的 refs 模拟。"""
    async with sem:
        gold = set(row["gold"])
        try:
            vector = await embed_text(row["query"])
            candidates = await search_faq_v3(row["query"], vector,
                                             top_k=settings.RERANK_CANDIDATES)
            ranked = await rerank(
                row["query"],
                [build_rerank_doc(h) for h in candidates],
                top_n=len(candidates),
            ) or []
        except Exception as e:  # noqa: BLE001 —— 单条失败跳过并记录
            row["_error"] = str(e)
            return row

        score_by_idx = dict(ranked)
        # 正样本：gold 命中候选的最高分（per-query 最佳相关条目得分）
        gold_scores = [
            score_by_idx[i] for i, h in enumerate(candidates)
            if h.get("question", "") in gold and i in score_by_idx
        ]
        row["_pos_best"] = max(gold_scores) if gold_scores else None

        # 三种口径的 top3 refs（score 字段仅为调试回看，不参与指标）
        rrf_refs = [{"question": h.get("question", "")} for h in candidates[:3]]
        rerank_order = [i for i, _ in sorted(ranked, key=lambda x: x[1], reverse=True)]
        rerank_refs = [{"question": candidates[i].get("question", "")}
                       for i in rerank_order[:3]]
        graded_order = [i for i in rerank_order if score_by_idx[i] >= settings.RERANK_T_MID]
        graded_refs = [{"question": candidates[i].get("question", "")}
                       for i in graded_order[:3]]

        row["_refs"] = {
            "rrf_top3": rrf_refs,
            "rerank_top3": rerank_refs,
            "rerank_graded": graded_refs,
        }
        if gold:
            row["_metrics"] = {name: _metrics(refs, gold)
                               for name, refs in row["_refs"].items()}
        else:
            # 负样本：最高分即分级后会进 refs 的最强条目分数
            row["_neg_max"] = max(score_by_idx.values()) if score_by_idx else 0.0
        return row


def _summarize(rows: list[dict]) -> dict:
    in_domain = [r for r in rows if r.get("_metrics")]
    ood = [r for r in rows if "_neg_max" in r]

    pos_best = [r["_pos_best"] for r in in_domain if r.get("_pos_best") is not None]
    neg_max = [r["_neg_max"] for r in ood]

    t_high = _quantile(neg_max, 0.99)
    t_mid = _quantile(neg_max, 0.95)
    t_low = _quantile(neg_max, 0.50)

    # 回验：正样本 per-query 存活率（至少一条 gold 候选过 T_MID 线）
    survival = (sum(1 for r in in_domain
                    if r.get("_pos_best") is not None and r["_pos_best"] >= t_mid)
                / len(in_domain)) if in_domain else 0.0
    # EER 参考：正负分布交点（FPR ≈ 1 - TPR），供分布重叠时人工判断
    eer = 0.0
    if pos_best and neg_max:
        best_err, eer = 1.0, t_mid
        for cand in sorted(set(round(x, 3) for x in pos_best + neg_max)):
            fpr = sum(1 for x in neg_max if x >= cand) / len(neg_max)
            fnr = sum(1 for x in pos_best if x < cand) / len(pos_best)
            if abs(fpr - fnr) < best_err:
                best_err, eer = abs(fpr - fnr), cand

    conflict = survival < 0.95
    summary = {
        "thresholds": {
            "T_HIGH": round(t_high, 4),
            "T_MID": round(t_mid, 4),
            "T_LOW": round(t_low, 4),
            "rules": "T_HIGH=neg_max P99；T_MID=neg_max P95；T_LOW=neg_max P50",
        },
        "validation": {
            "positive_survival_at_T_MID": round(survival, 3),
            "positive_survival_target": 0.95,
            "ood_false_admission_at_T_MID": round(
                sum(1 for x in neg_max if x >= t_mid) / len(neg_max), 3) if neg_max else 0.0,
            "ood_high_conf_at_T_HIGH": round(
                sum(1 for x in neg_max if x >= t_high) / len(neg_max), 3) if neg_max else 0.0,
            "eer_reference": eer,
            "distribution_conflict_warning": conflict,
        },
        "distributions": {
            "positive_best_gold_score": _percentile_table(pos_best),
            "negative_max_score": _percentile_table(neg_max),
        },
    }

    # 三口径对照（域内指标）
    for name in ("rrf_top3", "rerank_top3", "rerank_graded"):
        summary[name] = _agg([r["_metrics"][name] for r in in_domain])

    # 分级误杀清单（正样本最佳 gold 分数 < T_MID，将被整体兜底话术拦截的域内问题）
    summary["killed_in_domain"] = [
        {"query": r["query"], "pos_best": r["_pos_best"]}
        for r in in_domain
        if r.get("_pos_best") is not None and r["_pos_best"] < t_mid
    ][:10]
    return summary


def _print_summary(s: dict) -> None:
    t = s["thresholds"]
    v = s["validation"]
    print("=== 重排置信度阈值校准（bge-reranker-v2-m3 本地，口径=RRF候选池top10全量重排） ===")
    print(f"推荐阈值: T_HIGH={t['T_HIGH']}  T_MID={t['T_MID']}  T_LOW={t['T_LOW']}  ({t['rules']})")
    print(f"回验: 正样本存活率={v['positive_survival_at_T_MID']} (目标≥{v['positive_survival_target']})"
          f"  域外误进率={v['ood_false_admission_at_T_MID']}  高置信误召回={v['ood_high_conf_at_T_HIGH']}"
          f"  EER参考={v['eer_reference']}")
    if v["distribution_conflict_warning"]:
        print("⚠ 正负分布重叠：T_MID 下正样本存活率不达标，建议取正样本 P5 与负样本 P95 的中点并人工确认")
    d = s["distributions"]
    print(f"正样本分布(gold最佳分): {_percentile_str(d['positive_best_gold_score'])}")
    print(f"负样本分布(域外最高分): {_percentile_str(d['negative_max_score'])}")
    print("--- 三口径对照（域内 hit@1 / recall@3 / MRR） ---")
    for name, label in (("rrf_top3", "RRF top3(基线)"), ("rerank_top3", "重排 top3"),
                        ("rerank_graded", "重排+分级(线上)")):
        m = s[name]
        print(f"  {label}: n={m['n']}  hit@1={m['hit@1']}  recall@3={m['recall@3']}  MRR={m['mrr']}")
    if s["killed_in_domain"]:
        print(f"--- 分级误杀 {len(s['killed_in_domain'])} 条示例（域内问题被兜底拦截） ---")
        for k in s["killed_in_domain"]:
            print(f"  [pos_best={k['pos_best']:.4f}] {k['query']}")


def _percentile_str(tbl: dict) -> str:
    return " ".join(f"{k}={v}" for k, v in tbl.items() if k != "n") + f"  (n={tbl['n']})"


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条（快测）")
    args = ap.parse_args()

    rows = _load()
    if args.limit:
        rows = rows[: args.limit]
    print(f"加载 {len(rows)} 条（covered {sum(1 for r in rows if r['type'] == 'covered')}"
          f" / multi {sum(1 for r in rows if r['type'] == 'multi')}"
          f" / robust {sum(1 for r in rows if r['type'] == 'robust')}）")
    print(f"当前占位阈值: T_HIGH={settings.RERANK_T_HIGH} T_MID={settings.RERANK_T_MID} "
          f"T_LOW={settings.RERANK_T_LOW}")

    sem = asyncio.Semaphore(CONCURRENCY)
    t0 = time.perf_counter()
    rows = list(await asyncio.gather(*(_eval_one(r, sem) for r in rows)))
    elapsed = round(time.perf_counter() - t0, 1)

    errors = [r for r in rows if r.get("_error")]
    rows = [r for r in rows if not r.get("_error")]
    summary = _summarize(rows)
    _print_summary(summary)
    if errors:
        print(f"错误 {len(errors)} 条（已从统计中剔除，首条: {errors[0].get('_error', '')[:120]}）")

    REPORTS.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS / f"calibration_report_{ts}.json"
    report_path.write_text(
        json.dumps({"generated_at": datetime.now().isoformat(), "elapsed_s": elapsed,
                    "summary": summary}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"报告已写入 {report_path}（耗时 {elapsed}s）")
    print("下一步：确认阈值后回填 app/core/config.py 的 RERANK_T_HIGH/T_MID/T_LOW，"
          "再重跑 scripts/eval/run_retrieval_eval.py 验证线上口径")


if __name__ == "__main__":
    asyncio.run(main())
