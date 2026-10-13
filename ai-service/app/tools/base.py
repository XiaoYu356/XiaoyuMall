"""工具公共助手：身份注入、Prometheus 打点、统一可读错误契约。

设计要点：
- user_id/session_id 经 RunnableConfig 注入（API 层写入 config["configurable"]），
  LLM 不提供用户身份，也无法伪造
- 所有工具主体经 timed_call 包装：耗时/成败打 prometheus 指标；任何异常
  （上游超时/5xx/传输失败/业务失败）统一转成可读中文错误文本返回，不向图抛裸异常
- GraphInterrupt（HITL 硬中断）是 langgraph 的控制流信号，必须原样放行，
  绝不能被兜底 except 吞掉
"""
import time
from typing import Awaitable, Callable, Optional

import httpx
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphBubbleUp

from app.core.http_client import UpstreamError
from app.core.observability import tool_calls_total, tool_latency_seconds


class ToolError(Exception):
    """工具业务失败：message 为面向用户的可读文本（计入工具失败指标）。"""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _current_user_id(config: RunnableConfig) -> Optional[str]:
    """从运行时配置取当前用户ID（API 层写入 configurable，未登录为 None）。"""
    configurable = (config or {}).get("configurable") or {}
    user_id = configurable.get("user_id")
    return str(user_id) if user_id else None


def _current_session_id(config: RunnableConfig) -> Optional[str]:
    """从运行时配置取当前会话ID（API 层写入 configurable），供审计落库使用。"""
    configurable = (config or {}).get("configurable") or {}
    session_id = configurable.get("session_id")
    return str(session_id) if session_id else None


def _friendly_error(exc: Exception, service: str) -> str:
    """把上游异常转成可读中文错误文本。"""
    if isinstance(exc, UpstreamError):
        return f"抱歉，{service}暂时不可用，请稍后再试。"
    if isinstance(exc, httpx.TimeoutException):
        return f"抱歉，{service}响应超时，请稍后再试。"
    if isinstance(exc, httpx.HTTPStatusError):
        return f"抱歉，{service}返回异常（HTTP {exc.response.status_code}），请稍后再试。"
    return f"抱歉，{service}处理出现问题，请稍后再试。"


async def timed_call(
    tool_name: str,
    coro_factory: Callable[[], Awaitable[str]],
    service: str = "服务",
    ok_extractor: Callable[[str], bool] | None = None,
) -> str:
    """计时执行工具主体并打点；异常统一转可读文本返回，不向图抛裸异常。

    - tool_calls_total{tool, ok:"true"/"false"} 计数，tool_latency_seconds{tool} 记耗时
    - GraphBubbleUp（含 HITL 的 GraphInterrupt）原样放行：不打点、不吞、不转换
    - ok_extractor：可选，从成功结果判定业务成败（默认无异常即成功）
    """
    start = time.perf_counter()
    try:
        result = await coro_factory()
    except GraphBubbleUp:
        # HITL 硬中断：langgraph 借异常暂停图执行，必须透传给图运行时
        raise
    except ToolError as e:
        result, ok = e.message, "false"
    except Exception as e:  # noqa: BLE001 —— 工具层兜底：错误转可读文本，不中断图
        result, ok = _friendly_error(e, service), "false"
    else:
        ok = "true" if ok_extractor is None else bool(ok_extractor(result))
    tool_calls_total.labels(tool=tool_name, ok=ok).inc()
    tool_latency_seconds.labels(tool=tool_name).observe(time.perf_counter() - start)
    return result
