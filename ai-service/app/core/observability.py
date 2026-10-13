"""可观测层：structlog JSON 日志 + Prometheus 指标 + Langfuse 回调构建。

- setup_logging()：structlog JSON 输出，并让 stdlib root/uvicorn logger 也走同一 JSON 格式
- 指标为模块级单例（prometheus 默认全局 registry），/metrics 经 generate_latest 导出
- build_langfuse_callback()：未配 key 返回 (None, None)；Langfuse 任何故障不阻断主服务
"""
import logging
import sys
from typing import Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# ---- Prometheus 指标（模块级单例，默认全局 registry，/metrics 可导出） ----
from prometheus_client import (  # noqa: E402
    Counter,
    Gauge,
    Histogram,
)

# SSE 请求结果计数（complete/error/rejected 等）
sse_requests_total = Counter(
    "sse_requests_total",
    "SSE chat requests total by outcome",
    ["outcome"],
)
# 首个 LLM chunk 到达耗时（Time To First Token）
ttft_seconds = Histogram(
    "ttft_seconds",
    "Time to first LLM token in seconds",
)
# 端到端请求耗时（served_by 区分 agent/降级链路）
e2e_latency_seconds = Histogram(
    "e2e_latency_seconds",
    "End-to-end request latency in seconds",
    ["served_by"],
)
# 工具调用计数（tool 名称 + 是否成功）
tool_calls_total = Counter(
    "tool_calls_total",
    "Tool calls total",
    ["tool", "ok"],
)
# 工具调用耗时
tool_latency_seconds = Histogram(
    "tool_latency_seconds",
    "Tool call latency in seconds",
    ["tool"],
)
# LLM token 用量（type: input/output）
llm_tokens_total = Counter(
    "llm_tokens_total",
    "LLM tokens total",
    ["type"],
)
# 限流触发计数（scope: user/global）
rate_limited_total = Counter(
    "rate_limited_total",
    "Rate limited requests total",
    ["scope"],
)
# 当前活跃 SSE 连接数
sse_active_connections = Gauge(
    "sse_active_connections",
    "Currently active SSE connections",
)

# structlog 与 stdlib 共用的前置 processors（contextvars 携带 request_id 等）
_SHARED_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
]


def setup_logging() -> None:
    """配置 JSON 日志：structlog 与 stdlib（root/uvicorn）统一走同一格式。"""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # structlog 自身：输出 wrap 成 stdlib record，交给统一 handler 渲染
    structlog.configure(
        processors=_SHARED_PROCESSORS
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # stdlib 日志（含 uvicorn/root 与 logging.getLogger 使用方）渲染为 JSON
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
        foreign_pre_chain=_SHARED_PROCESSORS,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # uvicorn 自带 logger 也统一到 JSON 输出
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.addHandler(handler)
        uv_logger.propagate = False


def build_langfuse_callback() -> tuple[Optional[object], Optional[str]]:
    """构建 (Langfuse LangChain 回调, trace_url)；未配 key 或初始化失败返回 (None, None)。

    v4 SDK 适配：凭证显式初始化全局单例（Langfuse()），CallbackHandler 复用
    单例上报；预生成 trace_id 注入 trace_context，使 trace_url 在请求开始时
    即可回传前端（v4 的 CallbackHandler 不再自带 get_trace_url）。
    Langfuse 任何故障不阻断主服务。
    """
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        return None, None
    try:
        import uuid

        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler

        client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST or None,
        )
        trace_id = uuid.uuid4().hex  # 32 位小写 hex（OTel trace id 规范）
        callback = CallbackHandler(trace_context={"trace_id": trace_id})
        return callback, client.get_trace_url(trace_id=trace_id)
    except Exception as e:  # Langfuse 故障绝不能阻断主服务
        logger.warning("langfuse_callback_init_failed", error=str(e))
        return None, None
