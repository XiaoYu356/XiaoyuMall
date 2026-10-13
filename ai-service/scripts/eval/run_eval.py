"""v3 Agent 离线评测脚手架：跑批 golden_set.jsonl → 确定性断言 + LLM 裁判 → 报告。

用法（cwd=ai-service）：
    .venv\\Scripts\\python.exe scripts\\eval\\run_eval.py                  # 全量（enabled != false）
    .venv\\Scripts\\python.exe scripts\\eval\\run_eval.py --judge          # 追加 LLM 裁判打分
    .venv\\Scripts\\python.exe scripts\\eval\\run_eval.py --category faq,coupon
    .venv\\Scripts\\python.exe scripts\\eval\\run_eval.py --case faq_001,order_001

用例字段（golden_set.jsonl，每行一个 JSON）：
    id / category / q / user_id / note / enabled(false=跳过)
    expect:
        tools_any        期望调用的工具（命中任一即过）
        tools_forbidden  禁止出现的工具（逐个断言）
        no_tools         true = 不应调用任何工具
        interrupt        期望是否触发 HITL 硬中断
        resume           interrupt 后的恢复动作：true=批准(真实写库!) / false=拒绝 / 不填=不恢复
        blocked          true = 应被注入安全门拦截（不进图）
        cards_min / card_ids / citations_min
        min_text_len / must_mention / must_not_mention

指标口径：
    ttft_ms  = 首个正文流式 token 距用例开始（工具调用轮次的 tool_call_chunks 不计入）
    total_ms = 单条用例（含 resume 恢复）总耗时
runner 复用 chat.py 的事件捕获口径（on_tool_start/end + on_chat_model_*，node=agent/tools），
但不走 SSE 安全门以外的层；注入用例复用 detect_injection 模拟线上安全门行为。
报告写入 scripts/eval/reports/eval_report_<ts>.json。
"""
import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AI_ROOT))

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.api.chat import TOOL_NAMES, _content_text, _pending_interrupts
from app.core.http_client import close_http_client, init_http_client
from app.core.observability import setup_logging
from app.core.security import detect_injection, sanitize_input
from app.graph.builder import build_graph
from app.graph.checkpointer import checkpointer_mode, init_checkpointer
from app.tools import ALL_TOOLS  # noqa: F401  保证 TOOL_NAMES 与注册工具一致

GOLDEN_SET = Path(__file__).resolve().parent / "golden_set.jsonl"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"

_JUDGE_SYSTEM = (
    "你是电商客服 AI 的回答质量评审员。根据用户问题、助手回答和它调用的工具列表，"
    "从三个维度打 1-5 分：relevance(答是否对题)、groundedness(有无编造数据/政策，"
    "实时数据是否都来自工具)、conciseness(简洁不啰嗦)。verdict: 总体可用为 pass，"
    "答非所问或编造事实为 fail。reason 用一句话。只输出 JSON："
    '{"relevance": 1-5, "groundedness": 1-5, "conciseness": 1-5, '
    '"verdict": "pass"或"fail", "reason": "..."}'
)

# 工具层 _friendly_error 的错误关键词（timed_call 把异常转可读文本时的模式）
_TOOL_ERROR_PATTERNS = (
    "抱歉，", "暂时不可用", "响应超时", "请求失败",
    "失败", "错误", "不存在", "暂无相关说明",
)


def _extract_json(text: str) -> dict:
    """容忍 ```json 包裹 / 前后缀文字，提取第一个平衡 JSON 对象。"""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"裁判输出无 JSON: {text[:120]}")
    return json.loads(m.group(0))


async def judge_answer(judge_llm, q: str, answer: str, tools: list, context: str = "") -> dict:
    """LLM 裁判：对通过确定性断言的回答打分，失败不影响确定性结论。"""
    try:
        user_msg = (
            f"用户问题：{q}\n调用的工具：{tools or ['(无)']}\n"
            f"{context + chr(10) if context else ''}"
            f"助手回答：\n{answer}"
        )
        resp = await judge_llm.ainvoke(
            [{"role": "system", "content": _JUDGE_SYSTEM},
             {"role": "user", "content": user_msg}]
        )
        data = _extract_json(_content_text(resp.content))
        return {
            "relevance": int(data.get("relevance") or 0),
            "groundedness": int(data.get("groundedness") or 0),
            "conciseness": int(data.get("conciseness") or 0),
            "verdict": data.get("verdict"),
            "reason": data.get("reason", ""),
        }
    except Exception as e:  # 裁判自身故障不阻断评测
        return {"error": str(e)}


def _final_text_from_state(state) -> str:
    """checkpoint 最后一条非空 AIMessage（与 chat.py 收尾口径一致）。"""
    from langchain_core.messages import AIMessage

    for msg in reversed((getattr(state, "values", None) or {}).get("messages") or []):
        if isinstance(msg, AIMessage):
            text = _content_text(msg.content)
            if text:
                return text
    return ""


def _final_text_from_dict(result: dict) -> str:
    from langchain_core.messages import AIMessage

    for msg in reversed(result.get("messages", []) or []):
        if isinstance(msg, AIMessage):
            text = _content_text(msg.content)
            if text:
                return text
    return ""


async def run_case(graph, case: dict, judge_llm) -> dict:
    """跑单条用例：捕获工具轨迹/卡片/引用/文本/interrupt → 断言 → 可选裁判。"""
    expect = case.get("expect") or {}
    user_id = str(case.get("user_id", "1"))
    session_id = f"eval_{case['id']}_{int(time.time())}"
    q = sanitize_input(case["q"])
    r = {
        "id": case["id"], "category": case.get("category", ""), "q": q,
        "tools_called": [], "tool_calls_detail": [], "cards": [], "citations": [],
        "text": "", "interrupt": False, "resumed": None, "blocked": False,
        "input_tokens": 0, "output_tokens": 0, "ttft_ms": None, "total_ms": None,
        "checks": [], "passed": None, "judge": None,
    }

    # --- 安全门（模拟 chat_stream 的注入拦截：命中即降级、不进图） ---
    if detect_injection(q):
        r["blocked"] = True
        r["total_ms"] = 0
        if expect.get("blocked"):
            r["passed"] = True
            r["checks"].append(["injection_gate", True, "命中注入规则并被拦截"])
        else:
            r["passed"] = False
            r["checks"].append(["injection_gate", False, "非注入用例被误拦"])
        return r
    if expect.get("blocked"):
        r["total_ms"] = 0
        r["passed"] = False
        r["checks"].append(["injection_gate", False, "注入用例未被安全门拦截"])
        return r

    start = time.perf_counter()
    config = {
        "configurable": {
            "thread_id": f"u{user_id}:s{session_id}",
            "user_id": user_id,
            "session_id": session_id,
        },
        "recursion_limit": 25,
    }
    # 与 chat.py 一致：带 product_id 时把正在浏览的商品拼进 query 上下文
    query_text = q
    if case.get("product_id"):
        query_text = f"{q}\n\n[上下文] 用户当前正在查看商品ID: {case['product_id']}"
    graph_input = {"messages": [HumanMessage(content=query_text)], "user_id": user_id,
                   "session_id": session_id, "user_context": ""}

    streamed_parts: list[str] = []
    streamed_runs: set = set()
    tool_starts: dict = {}
    tool_ok_map: dict = {}  # run_id -> bool (on_tool_end 时判断)
    tool_output_map: dict = {}  # run_id -> str (原始输出，用于失败判断)
    ttft_at = None
    try:
        async for event in graph.astream_events(graph_input, config, version="v2"):
            etype = event.get("event")
            node = (event.get("metadata") or {}).get("langgraph_node")
            run_id = event.get("run_id")

            if etype == "on_chat_model_stream" and node == "agent":
                chunk = event["data"].get("chunk")
                if chunk is not None and getattr(chunk, "tool_call_chunks", None):
                    streamed_runs.add(run_id)
                    continue
                text = _content_text(chunk.content) if chunk is not None else ""
                if text:
                    streamed_runs.add(run_id)
                    streamed_parts.append(text)
                    if ttft_at is None:
                        ttft_at = time.perf_counter()

            elif etype == "on_chat_model_end" and node == "agent":
                usage = getattr(event["data"].get("output"), "usage_metadata", None) or {}
                r["input_tokens"] += int(usage.get("input_tokens") or 0)
                r["output_tokens"] += int(usage.get("output_tokens") or 0)

            elif etype == "on_tool_start" and node == "tools" and event.get("name") in TOOL_NAMES:
                tool_starts[run_id] = time.perf_counter()
                r["tools_called"].append(event["name"])

            elif etype == "on_tool_end" and node == "tools" and event.get("name") in TOOL_NAMES:
                output = event["data"].get("output")
                raw_text = output.content if hasattr(output, "content") else str(output or "")
                tool_output_map[run_id] = raw_text
                # 成功/失败判断：工具层把异常转可读文本，匹配错误模式即失败
                is_ok = not any(p in raw_text for p in _TOOL_ERROR_PATTERNS)
                tool_ok_map[run_id] = is_ok

                elapsed_ms = 0
                if run_id in tool_starts:
                    elapsed_ms = int((time.perf_counter() - tool_starts[run_id]) * 1000)
                tool_name = event["name"]
                r["tool_calls_detail"].append({
                    "tool": tool_name, "ok": is_ok, "elapsed_ms": elapsed_ms,
                })

                # raw_text 才是实际返回文本（ToolResult 不可直接 json.loads）
                try:
                    payload = json.loads(raw_text)
                except (json.JSONDecodeError, TypeError):
                    payload = None
                if isinstance(payload, dict):
                    if payload.get("products"):
                        r["cards"].extend(payload["products"])
                    if payload.get("refs"):
                        r["citations"].extend(payload["refs"])

        state = await graph.aget_state(config)
        pending = _pending_interrupts(state)
        r["interrupt"] = bool(pending)

        r["text"] = _final_text_from_state(state) or "".join(streamed_parts)
        if pending and expect.get("resume") is not None:
            approved = bool(expect["resume"])
            result = await graph.ainvoke(Command(resume=approved), config)
            r["resumed"] = approved
            r["text"] = _final_text_from_dict(result) or r["text"]

        r["ttft_ms"] = int((ttft_at - start) * 1000) if ttft_at else None
        r["total_ms"] = int((time.perf_counter() - start) * 1000)
    except Exception as e:
        r["total_ms"] = int((time.perf_counter() - start) * 1000)
        r["checks"].append(["graph_run", False, f"执行异常: {e}"])
        r["passed"] = False
        return r

    _evaluate(r, expect)

    if judge_llm is not None and r["passed"] and r["text"]:
        # HITL 用例需向裁判说明确认语境，否则拒绝/批准后的如实转告会被误判为答非所问
        context = ""
        if expect.get("resume") is not None:
            context = (
                "背景：这是 HITL 写操作确认的测试场景，用户已在系统确认卡片上选择"
                f"[{'批准' if expect['resume'] else '拒绝'}]，"
                "助手如实转告系统的处理结果即为正确行为。"
            )
        r["judge"] = await judge_answer(judge_llm, r["q"], r["text"], r["tools_called"], context)
    return r


def _evaluate(r: dict, expect: dict) -> None:
    """确定性断言：全部通过才算 PASS，结果写入 r["checks"] / r["passed"]。"""
    checks: list = []

    def chk(name: str, ok: bool, detail: str = "") -> None:
        checks.append([name, bool(ok), detail])

    tools = r["tools_called"]
    if expect.get("no_tools"):
        chk("no_tools", not tools, f"期望不调工具，实际 {tools}")
    if expect.get("tools_any"):
        hit = [t for t in expect["tools_any"] if t in tools]
        chk("tools_any", hit, f"期望任一 {expect['tools_any']}，实际 {tools}")
    if expect.get("tools_all"):
        missing = [t for t in expect["tools_all"] if t not in tools]
        chk("tools_all", not missing,
            f"期望全部调用 {expect['tools_all']}，缺失 {missing}")
    for t in expect.get("tools_forbidden") or []:
        chk(f"forbid:{t}", t not in tools, f"禁用工具被调用，实际 {tools}")
    chk("interrupt", r["interrupt"] == bool(expect.get("interrupt")),
        f"期望 {bool(expect.get('interrupt'))}，实际 {r['interrupt']}")
    if expect.get("resume") is not None and r["interrupt"]:
        chk("resume_done", r["resumed"] == bool(expect["resume"]),
            f"期望 resume={bool(expect['resume'])}，实际 {r['resumed']}")
    if expect.get("cards_min"):
        chk("cards_min", len(r["cards"]) >= expect["cards_min"],
            f"期望 ≥{expect['cards_min']} 张卡片，实际 {len(r['cards'])}")
    if expect.get("card_ids"):
        got = {c.get("id") for c in r["cards"]}
        missing = set(expect["card_ids"]) - got
        chk("card_ids", not missing, f"期望卡片含 {expect['card_ids']}，缺失 {sorted(missing)}")
    if expect.get("citations_min"):
        chk("citations_min", len(r["citations"]) >= expect["citations_min"],
            f"期望 ≥{expect['citations_min']} 条引用，实际 {len(r['citations'])}")
    if expect.get("min_text_len"):
        chk("min_text_len", len(r["text"]) >= expect["min_text_len"],
            f"期望文本 ≥{expect['min_text_len']} 字，实际 {len(r['text'])}")
    for s in expect.get("must_mention") or []:
        chk("must_mention", s in r["text"], f"文本未包含「{s}」")
    for s in expect.get("must_not_mention") or []:
        chk("must_not_mention", s not in r["text"], f"文本包含「{s}」")

    r["checks"] = checks
    r["passed"] = all(c[1] for c in checks)


def _print_case(r: dict) -> None:
    mark = "PASS" if r["passed"] else "FAIL"
    tok = f"{r['input_tokens']}/{r['output_tokens']}"
    ttft = f"{r['ttft_ms']}ms" if r["ttft_ms"] is not None else "-"
    print(f"[{mark}] {r['id']} ({r['category']}) tools={r['tools_called']} "
          f"ttft={ttft} total={r['total_ms']}ms tok={tok}")
    for name, ok, detail in r["checks"]:
        if not ok:
            print(f"       ✗ {name}: {detail}")
    if r["interrupt"]:
        print(f"       interrupt 触发, resume={r['resumed']}")
    if r["judge"]:
        j = r["judge"]
        if "error" in j:
            print(f"       judge error: {j['error']}")
        else:
            print(f"       judge: {j['verdict']} rel={j['relevance']} "
                  f"ground={j['groundedness']} concise={j['conciseness']} — {j['reason']}")


def _summary(results: list, total_cases: int) -> dict:
    passed = sum(1 for r in results if r["passed"])
    by_cat: dict = {}
    for r in results:
        c = by_cat.setdefault(r["category"], {"total": 0, "passed": 0})
        c["total"] += 1
        c["passed"] += 1 if r["passed"] else 0
    judged = [r["judge"] for r in results if r.get("judge") and "error" not in r["judge"]]
    lat = [r["total_ms"] for r in results if r["total_ms"] is not None and not r["blocked"]]
    ttfts = [r["ttft_ms"] for r in results if r["ttft_ms"] is not None]

    # --- 工具调用指标 ---
    tool_calls = []  # [(tool, ok, elapsed_ms), ...]
    for r in results:
        for tc in r.get("tool_calls_detail") or []:
            tool_calls.append((tc["tool"], tc["ok"], tc["elapsed_ms"]))
    tool_by_name: dict = {}
    for tool, ok, elap in tool_calls:
        t = tool_by_name.setdefault(tool, {"total": 0, "ok": 0, "fail": 0, "elapsed_total": 0})
        t["total"] += 1
        if ok:
            t["ok"] += 1
        else:
            t["fail"] += 1
        t["elapsed_total"] += elap
    tool_summary = {}
    for tool, s in sorted(tool_by_name.items()):
        tool_summary[tool] = {
            "total": s["total"],
            "ok": s["ok"],
            "fail": s["fail"],
            "success_rate": round(s["ok"] / s["total"], 4) if s["total"] else None,
            "avg_elapsed_ms": round(s["elapsed_total"] / s["total"]) if s["total"] else None,
        }

    # 每用例工具调用次数分布
    per_case_tool_count = [len(r["tools_called"]) for r in results if not r["blocked"]]
    avg_tools_per_case = round(sum(per_case_tool_count) / len(per_case_tool_count), 2) if per_case_tool_count else 0

    # --- FAQ 检索质量（citations 里的 score） ---
    faq_scores: list[float] = []  # 所有被引用条目的 score
    faq_top3_scores: list[float] = []  # 每条用例 top-3 引用的 score 均值
    for r in results:
        if r["category"] == "faq" and r["citations"]:
            scores = [c.get("score", 0.0) for c in r["citations"]]
            faq_scores.extend(scores)
            top3 = sorted(scores, reverse=True)[:3]
            faq_top3_scores.append(sum(top3) / len(top3) if top3 else 0)

    def _percentile(data: list[float], pct: float) -> float | None:
        if not data:
            return None
        s = sorted(data)
        idx = int(len(s) * pct / 100)
        return round(s[min(idx, len(s) - 1)], 4)

    faq_score_summary = None
    if faq_scores:
        faq_score_summary = {
            "total_refs": len(faq_scores),
            "avg_all_refs": round(sum(faq_scores) / len(faq_scores), 4),
            "p50_all_refs": _percentile(faq_scores, 50),
            "p90_all_refs": _percentile(faq_scores, 90),
            "top3_avg_per_case": {
                "mean": round(sum(faq_top3_scores) / len(faq_top3_scores), 4) if faq_top3_scores else None,
                "p50": _percentile(faq_top3_scores, 50),
                "p90": _percentile(faq_top3_scores, 90),
            },
            # 低分被引用预警：RRF 分 <0.02 的条目被引用 = 可能误检
            "low_score_refs": sum(1 for s in faq_scores if s < 0.02),
        }

    # --- 效率指标 ---
    ttft_ratios = []  # ttft / total
    for r in results:
        if r["ttft_ms"] and r["total_ms"] and r["total_ms"] > 0:
            ttft_ratios.append(r["ttft_ms"] / r["total_ms"])
    avg_ttft_ratio = round(sum(ttft_ratios) / len(ttft_ratios), 3) if ttft_ratios else None

    text_lengths = [len(r["text"]) for r in results if r["text"]]
    total_tok = sum(r["input_tokens"] + r["output_tokens"] for r in results)
    total_text_len = sum(text_lengths)
    tok_per_char = round(total_tok / total_text_len, 1) if total_text_len else None

    return {
        "total": total_cases,
        "ran": len(results),
        "passed": passed,
        "pass_rate": round(passed / len(results), 4) if results else 0,
        "by_category": by_cat,
        "judge": {
            "count": len(judged),
            "avg_relevance": round(sum(j["relevance"] for j in judged) / len(judged), 2) if judged else None,
            "avg_groundedness": round(sum(j["groundedness"] for j in judged) / len(judged), 2) if judged else None,
            "judge_fail": sum(1 for j in judged if j.get("verdict") == "fail"),
        },
        "latency": {
            "avg_total_ms": round(sum(lat) / len(lat)) if lat else None,
            "avg_ttft_ms": round(sum(ttfts) / len(ttfts)) if ttfts else None,
            "avg_ttft_ratio": avg_ttft_ratio,
        },
        "tokens": {
            "input": sum(r["input_tokens"] for r in results),
            "output": sum(r["output_tokens"] for r in results),
            "total_per_char": tok_per_char,
        },
        "tools": {
            "total_calls": len(tool_calls),
            "success_rate": round(
                sum(1 for _, ok, _ in tool_calls if ok) / len(tool_calls), 4
            ) if tool_calls else None,
            "fail_count": sum(1 for _, ok, _ in tool_calls if not ok),
            "avg_per_case": avg_tools_per_case,
            "per_tool": tool_summary,
        },
        "faq_quality": faq_score_summary,
    }


async def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="v3 Agent 离线评测")
    ap.add_argument("--judge", action="store_true", help="对通过断言的回答追加 LLM 裁判打分")
    ap.add_argument("--category", default="", help="只跑指定域（逗号分隔，如 faq,coupon）")
    ap.add_argument("--case", default="", help="只跑指定用例 id（逗号分隔）")
    args = ap.parse_args()

    cases = []
    for line in GOLDEN_SET.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            cases.append(json.loads(line))
    if args.category:
        cats = {c.strip() for c in args.category.split(",") if c.strip()}
        cases = [c for c in cases if c.get("category") in cats]
    if args.case:
        ids = {c.strip() for c in args.case.split(",") if c.strip()}
        cases = [c for c in cases if c["id"] in ids]
    cases = [c for c in cases if c.get("enabled", True)]
    if not cases:
        print("没有可运行的用例（检查 --category/--case/enabled）")
        return

    try:
        setup_logging()
    except Exception:
        pass
    await init_http_client()
    try:
        checkpointer = await init_checkpointer()
        graph = build_graph(checkpointer)
        judge_llm = None
        if args.judge:
            from app.graph.llms import create_main_llm

            judge_llm = create_main_llm()
        print(f"== v3 Agent 评测：{len(cases)} 条用例 | "
              f"checkpointer={checkpointer_mode()} | judge={'on' if judge_llm else 'off'} ==\n")

        results = []
        for case in cases:
            r = await run_case(graph, case, judge_llm)
            _print_case(r)
            results.append(r)
            print()

        total = len(cases)
        s = _summary(results, total)
        print("== 汇总 ==")
        print(f"通过 {s['passed']}/{s['ran']} ({s['pass_rate']:.1%})")
        for cat, c in s["by_category"].items():
            print(f"  {cat}: {c['passed']}/{c['total']}")
        if s["judge"]["count"]:
            print(f"裁判: {s['judge']['count']} 条 | 平均相关 {s['judge']['avg_relevance']} "
                  f"平均事实 {s['judge']['avg_groundedness']} | 裁判判 fail {s['judge']['judge_fail']} 条")
        if s["latency"]["avg_ttft_ms"] is not None:
            print(f"平均 TTFT {s['latency']['avg_ttft_ms']}ms | "
                  f"平均总耗时 {s['latency']['avg_total_ms']}ms | "
                  f"tokens {s['tokens']['input']}/{s['tokens']['output']}")

        # --- 深层指标 ---
        t = s["tools"]
        if t["total_calls"]:
            print(f"\n== 工具调用 ==")
            print(f"总调用 {t['total_calls']} 次 | 成功率 {t['success_rate']:.1%} "
                  f"({t['fail_count']} 次失败) | 平均每用例 {t['avg_per_case']} 次")
            for tool, info in t["per_tool"].items():
                rate = f"{info['success_rate']:.1%}" if info['success_rate'] is not None else "-"
                avg_el = f"{info['avg_elapsed_ms']}ms" if info['avg_elapsed_ms'] else "-"
                print(f"  {tool}: {info['total']} 次, 成功率 {rate}, 平均耗时 {avg_el}")

        fq = s["faq_quality"]
        if fq:
            print(f"\n== FAQ 检索质量 ==")
            print(f"共 {fq['total_refs']} 条引用 | 全量 avg={fq['avg_all_refs']} "
                  f"p50={fq['p50_all_refs']} p90={fq['p90_all_refs']}")
            top3 = fq["top3_avg_per_case"]
            print(f"top-3 均值: avg={top3['mean']} p50={top3['p50']} p90={top3['p90']}")
            if fq["low_score_refs"]:
                print(f"⚠ 低分(<0.02)被引用 {fq['low_score_refs']} 处，可能误检")

        lat = s["latency"]
        if lat["avg_ttft_ratio"] is not None:
            print(f"\n== 效率 ==")
            print(f"TTFT 占总耗时比 {lat['avg_ttft_ratio']:.1%} "
                  f"(低=工具慢，高=模型慢) | "
                  f"每字 token 消耗 {s['tokens']['total_per_char']}")

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORTS_DIR / f"eval_report_{ts}.json"
        report = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "model": __import__("app.core.config", fromlist=["settings"]).settings.OPENAI_MODEL,
            "summary": s,
            "results": results,
        }
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n报告: {report_path}")
    finally:
        await close_http_client()


if __name__ == "__main__":
    asyncio.run(main())
