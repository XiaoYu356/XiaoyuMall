"""对话窗口选取（v4：intent 与 fast path 共用）。

不能直接 `messages[-N:]` 取最近窗口：模型可在一轮规划中并行调用多个工具，
checkpoint 尾部形如 `Human → AI(tool_calls×k) → Tool×k → AI(answer) → Human`，
按条数切窗口会以孤儿 ToolMessage 开头。OpenAI / DashScope 规范要求 tool 消息
必须紧跟带对应 tool_calls 的 assistant 消息，否则请求直接 400。
"""
from typing import List

from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage


def select_recent_messages(
    messages: List[BaseMessage], window: int
) -> List[BaseMessage]:
    """取最近 window 条并裁剪头部孤儿工具回复，保证对话序列合法。

    - 只丢弃"窗口起点被截断"的 ToolMessage（其配对的 AI(tool_calls) 已在窗口外）
    - 窗口内完整的 AI(tool_calls) → Tool 配对原样保留（合法且对多轮指代有用）
    - 清洗后为空时退化到最后一条用户消息；连用户消息都没有则返回空列表
      （调用方各自兜底，绝不把孤儿 ToolMessage 送进模型）

    注：窗口取自尾部，因此不存在"尾部 Tool 被切掉"的残缺配对。
    """
    if not messages:
        return []

    recent = list(messages[-window:]) if window > 0 else []
    start = 0
    while start < len(recent) and isinstance(recent[start], ToolMessage):
        start += 1
    recent = recent[start:]
    if recent:
        return recent

    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return [msg]
    return []
