"""检索层评测 runner（RAG 专项，独立于端到端 run_eval.py）。

直接调 search_faq 工具（embedding + 三路召回 + RRF + cross-encoder 重排分级），
不走 agent 图：快（~1s/条）、无主 LLM 干扰，专测检索质量本身。

评测集：scripts/eval/retrieval_set.jsonl（gen_retrieval_queries.py 生成）
    covered：query + gold=[标准 question]，算 hit@1 / Recall@3 / MRR / 分类统计
    robust ：无 gold（域外问题），统计重排最高分分布与阈值分级拦截效果
             refs 为空 = T_MID 分级剔除；score 为重排分数（raw logits，非 0~1 概率）

置信度阈值由 scripts/eval/calibrate_rerank_thresholds.py 在本评测集上校准，
高置信误召回判定线取 RERANK_T_HIGH（负样本 P99）。

运行（cwd=ai-service）：
    .venv\\Scripts\\python.exe -m scripts.eval.run_retrieval_eval [--limit N] [--category X]
报告写入 scripts/eval/reports/retrieval_report_{ts}.json。
"""
import argparse
import asyncio
import csv
import json
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.tools.faq_tools import search_faq

HERE = Path(__file__).parent
DATASET = HERE / "retrieval_set.jsonl"
REPORTS = HERE / "reports"
CONCURRENCY = 1  # 本地 GPU 推理非线程安全，串行跑
ROBUST_HIGH_CONF = settings.RERANK_T_HIGH  # 重排高置信线（校准产出，回填 config）


def _load() -> list[dict]:
    rows = []
    with DATASET.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _mean(xs: list[float]) -> float:
    return round(sum(xs) / len(xs), 4) if xs else 0.0


async def _eval_one(row: dict, sem: asyncio.Semaphore) -> dict:
    """单条评测：调 search_faq，保留 top3 的 question/score/category。"""
    async with sem:
        try:
            raw = await search_faq.ainvoke(row["query"])
            refs = json.loads(raw).get("refs", [])
        except Exception as e:
            refs = []
            row["_error"] = str(e)
        row["refs"] = [
            {"question": r.get("question", ""), "score": r.get("score", 0.0), "category": r.get("category", "")}
            for r in refs
        ]
        return row


def _metrics(row: dict) -> dict:
    """统一指标口径（gold 可为 1~5 条）：
    recall@3    = |top3 ∩ gold| / |gold|      —— 召回面
    precision@3 = |top3 ∩ gold| / 3            —— top3 里有多少条真相关（单 gold 时上限 1/3）
    hit@1 / MRR 按首个命中名次。
    """
    gset = set(row["gold"])
    refs = row["refs"]
    hits3 = sum(1 for r in refs[:3] if r["question"] in gset)
    rank = next((i for i, r in enumerate(refs, 1) if r["question"] in gset), 0)
    return {
        "hit1": 1 if rank == 1 else 0,
        "recall": hits3 / len(gset) if gset else 0.0,
        "precision": hits3 / 3,
        "mrr": 1.0 / rank if rank else 0.0,
    }


def _agg(rows: list[dict]) -> dict:
    ms = [_metrics(r) for r in rows]
    n = len(rows)
    if not n:
        return {"n": 0}
    return {
        "n": n,
        "hit@1": round(sum(m["hit1"] for m in ms) / n, 3),
        "recall@3": round(sum(m["recall"] for m in ms) / n, 3),
        "precision@3": round(sum(m["precision"] for m in ms) / n, 3),
        "mrr": round(sum(m["mrr"] for m in ms) / n, 3),
        "errors": sum(1 for r in rows if r.get("_error")),
    }


def _summarize(rows: list[dict]) -> dict:
    covered = [r for r in rows if r["type"] == "covered"]
    multi = [r for r in rows if r["type"] == "multi"]
    robust = [r for r in rows if r["type"] == "robust"]

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in covered:
        by_cat[r["category"]].append(r)
    cat_stat = {cat: _agg(rs) for cat, rs in sorted(by_cat.items())}

    robust_scores = [r["refs"][0]["score"] for r in robust if r["refs"]]
    robust_high = [r for r in robust if r["refs"] and r["refs"][0]["score"] >= ROBUST_HIGH_CONF]
    robust_empty = [r for r in robust if not r["refs"]]

    # multi 最差案例（precision 最低的 5 条，辅助分析 top3 被什么占位）
    multi_sorted = sorted(multi, key=lambda r: _metrics(r)["precision"])
    multi_worst = [{
        "query": r["query"],
        "gold_n": len(r["gold"]),
        "top3": [x["question"] for x in r["refs"][:3]],
        "gold_in_top3": sum(1 for x in r["refs"][:3] if x["question"] in set(r["gold"])),
    } for r in multi_sorted[:5]]

    total = _agg(covered + multi) if (covered or multi) else {"n": 0}

    return {
        "covered": {**_agg(covered), "by_category": cat_stat},
        "multi": {
            **_agg(multi),
            "avg_gold_n": round(sum(len(r["gold"]) for r in multi) / len(multi), 2) if multi else 0,
            "worst5": multi_worst,
        },
        "total_covered_plus_multi": total,
        "robust": {
            "n": len(robust),
            "top1_score_avg": _mean(robust_scores),
            # refs 为空 = T_MID 置信度分级剔除（重排后无条目过线）
            "graded_out": {
                "count": len(robust_empty),
                "ratio": round(len(robust_empty) / len(robust), 3) if robust else 0,
            },
            "high_conf_false_recall": {
                "threshold": ROBUST_HIGH_CONF,
                "count": len(robust_high),
                "ratio": round(len(robust_high) / len(robust), 3) if robust else 0,
                "cases": [{"query": r["query"], "top1": r["refs"][0]["question"], "score": r["refs"][0]["score"]}
                          for r in robust_high],
            },
        },
    }


def _export_detail_csv(rows: list[dict], ts: str) -> Path:
    """逐条结果记录（CSV，utf-8-sig 便于 Excel 直接打开）：每条 query 的 gold、top3 检索结果与命中指标。"""
    path = REPORTS / f"retrieval_detail_{ts}.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "type", "category", "query", "gold_n", "gold_questions",
                    "top1", "top1_score", "top2", "top2_score", "top3", "top3_score",
                    "gold_hits_in_top3", "recall@3", "precision@3", "hit@1", "mrr", "error"])
        for r in rows:
            m = _metrics(r)
            gset = set(r["gold"])
            hits = sum(1 for x in r["refs"][:3] if x["question"] in gset)
            padded = list(r["refs"]) + [None] * (3 - len(r["refs"]))
            top_cells: list[str] = []
            for x in padded[:3]:
                if x:
                    top_cells += [x.get("question", ""), f'{x.get("score", 0):.4f}']
                else:
                    top_cells += ["", ""]
            w.writerow([
                r["id"], r["type"], r["category"], r["query"], len(r["gold"]),
                " | ".join(r["gold"]),
                *top_cells, hits,
                round(m["recall"], 4), round(m["precision"], 4), m["hit1"], round(m["mrr"], 4),
                r.get("_error", ""),
            ])
    return path


def _print_summary(s: dict) -> None:
    c, m, rb = s["covered"], s["multi"], s["robust"]
    t = s["total_covered_plus_multi"]
    print("=== 检索层评测（三路召回+RRF+cross-encoder 重排分级，top_k=3） ===")
    print(f"总体（简单+复合问题合并，n={t.get('n', 0)}）:  hit@1={t.get('hit@1')}  recall@3={t.get('recall@3')}  precision@3={t.get('precision@3')}  MRR={t.get('mrr')}  错误={t.get('errors', 0)}")
    print("--- 分口径明细（供对照） ---")
    print(f"  covered（单 gold）: n={c.get('n', 0)}  hit@1={c.get('hit@1')}  recall@3={c.get('recall@3')}  precision@3={c.get('precision@3')}  MRR={c.get('mrr')}")
    print(f"  multi（复合 2~5 gold）: n={m.get('n', 0)}  平均gold={m.get('avg_gold_n')}  hit@1={m.get('hit@1')}  recall@3={m.get('recall@3')}  precision@3={m.get('precision@3')}")
    print("--- covered 分类明细（recall@3 升序） ---")
    for cat, st in sorted(c.get("by_category", {}).items(), key=lambda kv: kv[1].get("recall@3", 0)):
        flag = " ← 薄弱" if st.get("recall@3", 0) < 0.7 else ""
        print(f"  {cat}: n={st['n']} hit@1={st['hit@1']} recall@3={st['recall@3']} precision@3={st['precision@3']}{flag}")
    print("--- multi 最差 5 条（precision 升序，看 top3 被什么占位） ---")
    for w in m.get("worst5", []):
        print(f"  [gold {w['gold_in_top3']}/{w['gold_n']} 命中] {w['query']}")
        for q in w["top3"]:
            print(f"      - {q}")
    print(f"robust: n={rb['n']}  top1分均值={rb['top1_score_avg']}  高置信误召回={rb['high_conf_false_recall']['count']}/{rb['n']} ({rb['high_conf_false_recall']['ratio']})  判级剔除={rb.get('graded_out', {}).get('count', 0)}/{rb['n']}")
    for case in rb["high_conf_false_recall"]["cases"][:10]:
        print(f"  [误召回 {case['score']:.4f}] {case['query']} → {case['top1']}")
    print("判定参考：total recall@3 ≥85% 优秀；precision@3 反映 top3 相关密度，域外误召回率反映「自信答错」倾向")
    print("注：multi gold 为标注子集，precision@3 是保守下界（top3 中实际相关但未标注的条目会被计为噪声）")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条（快测）")
    ap.add_argument("--category", type=str, default="", help="只跑指定 category")
    args = ap.parse_args()

    rows = _load()
    if args.category:
        rows = [r for r in rows if r["category"] == args.category]
    if args.limit:
        rows = rows[: args.limit]
    print(f"加载 {len(rows)} 条（covered {sum(1 for r in rows if r['type'] == 'covered')} / multi {sum(1 for r in rows if r['type'] == 'multi')} / robust {sum(1 for r in rows if r['type'] == 'robust')}）")

    sem = asyncio.Semaphore(CONCURRENCY)
    t0 = time.perf_counter()
    rows = list(await asyncio.gather(*(_eval_one(r, sem) for r in rows)))
    elapsed = round(time.perf_counter() - t0, 1)

    summary = _summarize(rows)
    _print_summary(summary)

    REPORTS.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS / f"retrieval_report_{ts}.json"
    report_path.write_text(
        json.dumps({"generated_at": datetime.now().isoformat(), "elapsed_s": elapsed, "summary": summary,
                    "detail": [{k: r[k] for k in ("id", "query", "gold", "category", "type", "refs") if k in r} for r in rows]},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    csv_path = _export_detail_csv(rows, ts)
    print(f"报告已写入 {report_path}（耗时 {elapsed}s）")
    print(f"逐条记录已写入 {csv_path}")


if __name__ == "__main__":
    asyncio.run(main())
