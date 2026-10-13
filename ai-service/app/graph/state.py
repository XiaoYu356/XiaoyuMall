"""LangGraph 图状态定义（v3：单 Agent，无任何意图/路由字段）。"""
from typing import Annotated, Optional, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict, total=False):
    # 对话消息（add_messages 归并：按 id 去重/替换/追加）
    messages: Annotated[list[AnyMessage], add_messages]

    # 会话标识（checkpointer 的 thread 维度由 API 层组装为 u{user}:s{session}）
    user_id: Optional[str]
    session_id: str

    # API 层注入：用户偏好等上下文摘要（拼入 system prompt）
    user_context: str
