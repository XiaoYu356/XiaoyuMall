"""GET /api/v1/ai/stream/v3/chat —— v3 SSE 对话端点（单 Agent 主干，契约见设计文档 §6）。

事件序列（每帧格式 `event: <type>\ndata: <json>\n\n`，json 不转义中文）：
    meta（首事件，request_id/trace_url/served_by="agent"）
    → intent（v4 路由决策 route/domain；v0 图无 intent 节点，不发此事件）
    → tool{start/end} → product_card / citation
    → llm_chunk（流式增量，首个 chunk 记 TTFT）
    → interrupt（HITL 写操作确认卡片，astream 自然结束后从 checkpoint 读取）
    → complete（usage: input/output tokens、total_ms、shortcut_hit=false）
    异常：error{code,message,recoverable} + complete

安全门在端点体内完成（401/429 可正常返回 HTTP 错误码）：
    get_request_user → check_rate_limit → acquire_sse_slot（生成器 finally 释放）；
    注入命中：发 meta → 固定降级文案 llm_chunk → complete，不进图（0 次 LLM/工具调用）。
"""
import json
import time
import uuid
from typing import Any, AsyncGenerator, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage

from app.core.observability import (
    build_langfuse_callback,
    e2e_latency_seconds,
    llm_tokens_total,
    sse_active_connections,
    sse_requests_total,
    ttft_seconds,
)
from app.core.security import (
    acquire_sse_slot,
    check_rate_limit,
    detect_injection,
    get_request_user,
    release_sse_slot,
    sanitize_input,
)
from app.graph.nodes.agent import split_for_model
from app.memory import get_redis
from app.memory.consolidator import maybe_consolidate
from app.memory.history import add_message
from app.memory.profile import get_relevant_preferences
from app.memory.summary import get_summary, schedule_summary_update
from app.tools import ALL_TOOLS

logger = structlog.get_logger(__name__)

router = APIRouter()

# 偏好字段 → 提示词中的中文标签（未登记的字段原样输出）
_PREF_LABELS = {
    "favorite_categories": "偏好品类",
    "favorite_brands": "偏好品牌",
    "price_range": "偏好价位",
    "other_notes": "其他偏好",
}


def _format_preferences(items: list) -> str:
    """把 top-k 原子偏好拼成一行注入文本（列表值用顿号连接）。"""
    parts = []
    for item in items:
        label = _PREF_LABELS.get(item.get("k"), item.get("k"))
        value = item.get("v")
        if isinstance(value, (list, tuple)):
            value = "、".join(str(v) for v in value)
        parts.append(f"{label}: {value}")
    return "；".join(parts)


# 注册到图的工具名白名单（SSE 层只透出业务工具事件，防内部杂散 run 混入；
# v4 fast path 直调 search_faq 挂在 faq_answer 节点下，故不按图节点过滤、只认白名单）
TOOL_NAMES = {t.name for t in ALL_TOOLS}
# 产出流式回答文本的 LLM 节点（v4：agent + 两个 fast path 回答节点）
_STREAM_LLM_NODES = {"agent", "small_talk", "faq_answer"}
# token 用量统计节点（额外包含非流式的 intent 路由模型）
_LLM_USAGE_NODES = _STREAM_LLM_NODES | {"intent"}
# on_chain_end 时需切块补发 llm_chunk 的节点：clarify/human_transfer 无 LLM 调用，
# faq_answer 检索为空走固定兜底文案时无模型流（有模型流时由 streamed_nodes 去重）
_PASSTHROUGH_TEXT_NODES = {"clarify", "human_transfer", "faq_answer"}
# 快速通道 route：未进 ReAct 循环即直出（用于 complete 的 shortcut_hit 与观测维度）
_SHORTCUT_ROUTES = {"small_talk", "faq_answer", "clarify", "human_transfer"}
# 结构化输出工具：end 时输出必须可解析为 JSON，否则视为失败（ok=false）
_STRUCTURED_TOOLS = {"search_products", "get_product_detail", "search_faq"}
# 兜底补发切块大小（旧版库 streaming 失效场景，~80 字/块模拟流式）
_FALLBACK_CHUNK_SIZE = 80
# 注入命中固定降级文案
_DEGRADED_ANSWER = "抱歉，您的输入包含系统无法处理的内容，请重新描述您的问题。"


def _sse(event_type: str, data: dict) -> str:
    """v3 SSE 帧：event 行 + data 行（json ensure_ascii=False）。"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _content_text(content: Any) -> str:
    """消息 content → 纯文本（str 直返；多模态块列表拼接其中的 text 段）。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "".join(parts)
    return ""


def _pending_interrupts(state: Any) -> list:
    """从 StateSnapshot 健壮读取挂起的 interrupt（langgraph 1.x 以实际返回结构为准）。

    优先直接取 state.interrupts（1.2.12 已有该字段），缺失时回退遍历 tasks 聚合。
    """
    pending = getattr(state, "interrupts", None)
    if pending:
        return list(pending)
    return [
        intr
        for task in (getattr(state, "tasks", None) or [])
        for intr in (getattr(task, "interrupts", None) or ())
    ]


@router.get("/api/v1/ai/stream/v3/chat")
async def chat_stream(
    request: Request,
    q: str,
    session_id: Optional[str] = None,
    product_id: Optional[int] = None,
    user_id: str = Depends(get_request_user),
):
    """SSE 对话（v3 契约）。身份缺失 401、限流/连接超限 429 由安全门抛出。"""
    graph = getattr(request.app.state, "ai_graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="AI 服务尚未就绪，请稍后再试")

    # 安全门：限流 → SSE 连接槽位（生成器 finally 中释放）
    redis = get_redis()
    await check_rate_limit(redis, user_id)
    slot_key = await acquire_sse_slot(redis, user_id)

    # 会话缺省生成 uuid，经 meta 事件回传给前端
    session_id = session_id or uuid.uuid4().hex

    return StreamingResponse(
        _chat_event_stream(
            graph=graph,
            q=q,
            user_id=user_id,
            session_id=session_id,
            product_id=product_id,
            redis=redis,
            slot_key=slot_key,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _chat_event_stream(
    *,
    graph,
    q: str,
    user_id: str,
    session_id: str,
    product_id: Optional[int],
    redis,
    slot_key: str,
) -> AsyncGenerator[str, None]:
    """核心事件流：安全处理 → 翻译 astream_events → HITL/收尾/异常。"""
    request_id = uuid.uuid4().hex
    structlog.contextvars.bind_contextvars(request_id=request_id, user_id=user_id)
    start = time.perf_counter()
    input_tokens = 0
    output_tokens = 0
    ttft_recorded = False
    try:
        sse_active_connections.inc()
        q = sanitize_input(q)

        # Langfuse trace（未配 key 为 (None, None)，任何故障不阻断主流程）
        cb, trace_url = build_langfuse_callback()

        # meta 首事件（session_id 一并回传，供前端后续请求携带）
        yield _sse("meta", {
            "request_id": request_id,
            "trace_url": trace_url,
            "served_by": "agent",
            "session_id": session_id,
        })

        # 注入命中：降级应答，不进图（不调用 LLM/工具）
        # 注：structlog 首个位置参数即 JSON 的 event 字段，因此注入标记写为事件名
        if detect_injection(q):
            logger.warning(
                "injection_blocked",
                detail="提示注入命中，已降级应答",
                request_id=request_id,
                user_id=user_id,
            )
            yield _sse("llm_chunk", {"text": _DEGRADED_ANSWER})
            yield _sse("complete", {"usage": {
                "input_tokens": 0, "output_tokens": 0,
                "total_ms": int((time.perf_counter() - start) * 1000),
                "shortcut_hit": False,
            }})
            sse_requests_total.labels(outcome="ok").inc()
            e2e_latency_seconds.labels(served_by="agent", route="none").observe(
                time.perf_counter() - start
            )
            return

        # --- 组装输入：按相关性取 top-k 偏好 + 读取滚动摘要 + product_id 上下文 ---
        # 偏好/摘要都经 state 传给图，由 pre_model_hook 在裁剪之后注入：
        # 直接塞进 messages 会被 trim_messages(start_on='human') 丢掉
        user_context = ""
        try:
            prefs = await get_relevant_preferences(str(user_id), q, top_k=5)
            if prefs:
                user_context = _format_preferences(prefs)
        except Exception as e:
            logger.warning("读取用户偏好失败(忽略)", error=str(e))

        try:
            memory_summary = await get_summary(str(user_id), session_id)
        except Exception as e:
            logger.warning("读取会话摘要失败(忽略)", error=str(e))
            memory_summary = ""

        query_text = q
        if product_id:
            query_text = f"{q}\n\n[上下文] 用户当前正在查看商品ID: {product_id}"
        input_messages = [HumanMessage(content=query_text)]

        graph_input = {
            "messages": input_messages,
            "user_id": str(user_id),
            "session_id": session_id,
            "user_context": user_context,
            "memory_summary": memory_summary,
        }

        thread_id = f"u{user_id}:s{session_id}"
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": str(user_id),
                "session_id": session_id,
            },
            "recursion_limit": 25,
        }
        if cb is not None:
            config["callbacks"] = [cb]

        full_text_parts: list[str] = []
        streamed_runs: set = set()   # 已产出流式 token 的模型轮次（兜底补发去重）
        streamed_nodes: set = set()  # 已产出流式文本的图节点（passthrough 补发去重）
        tool_starts: dict = {}       # run_id → 开始时刻（算 elapsed_ms）
        structured: dict = {}        # 结构化附件（cards/citations/draft），随助手消息持久化
        interrupted = False
        route: Optional[str] = None  # v1 路由去向（v0 图无 intent 节点，保持 None）

        # --- v0/v1 主干：翻译 astream_events 为 SSE 事件（节点名过滤对齐图装配） ---
        async for event in graph.astream_events(graph_input, config, version="v2"):
            etype = event.get("event")
            metadata = event.get("metadata") or {}
            node = metadata.get("langgraph_node")
            run_id = event.get("run_id")

            if etype == "on_chat_model_stream" and node in _STREAM_LLM_NODES:
                chunk = event["data"].get("chunk")
                # 工具调用轮次：content 是调用参数残片，跳过（tool 事件由 on_tool_start 发出）
                if chunk is not None and getattr(chunk, "tool_call_chunks", None):
                    streamed_runs.add(run_id)  # 阻止该轮 on_chat_model_end 兜底误发
                    continue
                text = _content_text(chunk.content) if chunk is not None else ""
                if text:
                    streamed_runs.add(run_id)
                    streamed_nodes.add(node)
                    full_text_parts.append(text)
                    if not ttft_recorded:
                        ttft_recorded = True
                        ttft_seconds.observe(time.perf_counter() - start)
                    yield _sse("llm_chunk", {"text": text})

            elif etype == "on_chat_model_end" and node in _LLM_USAGE_NODES:
                message = event["data"].get("output")
                # token 用量累计（usage_metadata 缺失时安全跳过）
                usage = getattr(message, "usage_metadata", None) or {}
                inc_in = int(usage.get("input_tokens") or 0)
                inc_out = int(usage.get("output_tokens") or 0)
                input_tokens += inc_in
                output_tokens += inc_out
                if inc_in:
                    llm_tokens_total.labels(type="input").inc(inc_in)
                if inc_out:
                    llm_tokens_total.labels(type="output").inc(inc_out)

                # 兜底补发：该轮次完全没发出过流式 token 时整段切块（正常流式不重复发）
                text = _content_text(message.content) if message is not None else ""
                if (
                    text
                    and run_id not in streamed_runs
                    and not getattr(message, "tool_calls", None)
                ):
                    streamed_runs.add(run_id)
                    streamed_nodes.add(node)
                    full_text_parts.append(text)
                    if not ttft_recorded:
                        ttft_recorded = True
                        ttft_seconds.observe(time.perf_counter() - start)
                    for i in range(0, len(text), _FALLBACK_CHUNK_SIZE):
                        yield _sse("llm_chunk", {"text": text[i:i + _FALLBACK_CHUNK_SIZE]})

            elif etype == "on_tool_start" and event.get("name") in TOOL_NAMES:
                tool_starts[run_id] = time.perf_counter()
                yield _sse("tool", {"name": event["name"], "phase": "start", "ok": True})

            elif etype == "on_tool_end" and event.get("name") in TOOL_NAMES:
                output = event["data"].get("output")
                if hasattr(output, "content"):  # 旧版可能返回 ToolMessage 而非纯字符串
                    output = output.content

                elapsed_ms = None
                started_at = tool_starts.pop(run_id, None)
                if started_at is not None:
                    elapsed_ms = int((time.perf_counter() - started_at) * 1000)

                # 结构化工具输出必须可解析 JSON，解析失败视为工具失败
                payload = None
                try:
                    payload = json.loads(output) if isinstance(output, str) else None
                except (json.JSONDecodeError, TypeError):
                    payload = None
                ok = not (
                    event.get("name") in _STRUCTURED_TOOLS
                    and not isinstance(payload, dict)
                )
                data = {"name": event["name"], "phase": "end", "ok": ok}
                if elapsed_ms is not None:
                    data["elapsed_ms"] = elapsed_ms
                yield _sse("tool", data)

                # 结构化输出 → 前端卡片事件（解析失败静默跳过），同时记录供持久化
                if isinstance(payload, dict):
                    if payload.get("products"):
                        structured["cards"] = payload["products"]
                        yield _sse("product_card", {"items": payload["products"]})
                    if payload.get("refs"):
                        structured["citations"] = payload["refs"]
                        yield _sse("citation", {"refs": payload["refs"]})

            elif etype == "on_chain_end" and node == "intent":
                # v4 路由决策透出（v0 图无 intent 节点，此分支不触发）
                output = event["data"].get("output")
                if isinstance(output, dict) and output.get("route"):
                    route = output["route"]
                    yield _sse("intent", {
                        "route": output["route"],
                        "domain": output.get("domain", "none"),
                    })

            elif etype == "on_chain_end" and node in _PASSTHROUGH_TEXT_NODES:
                # 无模型流的节点（clarify/human_transfer、faq_answer 空检索兜底），
                # 把节点产出的 AIMessage 切块补发为 llm_chunk，保证前端有可见文本
                if node in streamed_nodes:
                    continue
                output = event["data"].get("output")
                messages = output.get("messages") if isinstance(output, dict) else None
                if not messages:
                    continue
                text = _content_text(messages[-1].content)
                if not text:
                    continue
                streamed_nodes.add(node)
                full_text_parts.append(text)
                if not ttft_recorded:
                    ttft_recorded = True
                    ttft_seconds.observe(time.perf_counter() - start)
                for i in range(0, len(text), _FALLBACK_CHUNK_SIZE):
                    yield _sse("llm_chunk", {"text": text[i:i + _FALLBACK_CHUNK_SIZE]})

        # --- HITL：图在写工具 interrupt 处挂起时 astream 自然结束，
        # 从 checkpoint 读出待确认 payload，推给前端渲染确认卡片（按钮走 /resume 恢复） ---
        state = None
        try:
            state = await graph.aget_state(config)
        except Exception as e:
            logger.warning("读取图状态失败(忽略)", error=str(e))
        pending = _pending_interrupts(state) if state is not None else []
        if pending:
            interrupted = True
            value = pending[0].value
            action = (
                value.get("action", "confirm") if isinstance(value, dict) else "confirm"
            )
            structured["draft"] = value  # 确认卡片随消息持久化，刷新后可恢复确认
            yield _sse("interrupt", {
                "action": action,
                "payload": value,
                "resume_token": session_id,
            })

        # --- 滚动摘要：把本轮超出预算被裁剪的旧消息交给后台增量压缩，
        # 下一轮由 pre_model_hook 注入；不阻塞 SSE 收尾 ---
        try:
            state_messages = (getattr(state, "values", None) or {}).get("messages") or []
            if state_messages:
                _kept, dropped = split_for_model(state_messages)
                if dropped:
                    schedule_summary_update(str(user_id), session_id, dropped)
        except Exception as e:
            logger.warning("派发会话摘要更新失败(忽略)", error=str(e))

        # --- 收尾：final_text（checkpoint 最后一条非空 AIMessage，回退已累计流式文本） ---
        final_text = ""
        try:
            messages = (getattr(state, "values", None) or {}).get("messages") or []
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    text = _content_text(msg.content)
                    if text:
                        final_text = text
                        break
        except Exception as e:
            logger.warning("提取最终答复失败(忽略)", error=str(e))
        if not final_text:
            final_text = "".join(full_text_parts)

        # 会话记忆写入 + 记忆整理（最佳努力，不影响主流程）
        try:
            await add_message(str(user_id), session_id, "user", q)
            if final_text or structured:
                await add_message(str(user_id), session_id, "assistant", final_text,
                                  extra=structured or None)
            await maybe_consolidate(str(user_id), session_id)
        except Exception as e:
            logger.warning("写入会话记忆失败(忽略)", error=str(e))

        yield _sse("complete", {"usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_ms": int((time.perf_counter() - start) * 1000),
            "shortcut_hit": route in _SHORTCUT_ROUTES,
            "route": route,
        }})
        sse_requests_total.labels(
            outcome="interrupt" if interrupted else "ok"
        ).inc()
        e2e_latency_seconds.labels(
            served_by="agent", route=route or "none"
        ).observe(
            time.perf_counter() - start
        )

    except Exception as e:
        # 统一错误：可读信息 + recoverable 标记，前端提示重试
        logger.exception("SSE 对话处理异常", error=str(e))
        yield _sse("error", {
            "code": "INTERNAL_ERROR",
            "message": "服务处理出现问题，请稍后再试",
            "recoverable": True,
        })
        yield _sse("complete", {"usage": {
            "input_tokens": 0, "output_tokens": 0,
            "total_ms": int((time.perf_counter() - start) * 1000),
            "shortcut_hit": False,
        }})
        sse_requests_total.labels(outcome="error").inc()

    finally:
        structlog.contextvars.unbind_contextvars("request_id", "user_id")
        sse_active_connections.dec()
        try:
            await release_sse_slot(redis, user_id)
        except Exception:
            pass
