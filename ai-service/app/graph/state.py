"""LangGraph 图状态定义（v4：v0 单 Agent 不读写路由字段，v1 意图路由使用）。"""
from typing import Annotated, Optional

from typing_extensions import TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from langgraph.managed import RemainingSteps


class AgentGraphState(TypedDict, total=False):
    """v0 create_react_agent 的状态：在 messages 之外承载本轮注入的上下文。

    自定义 state_schema 后，chat.py 传入的 user_context / memory_summary
    才会进入图状态，pre_model_hook 才能在裁剪之后把它们拼回模型输入。
    remaining_steps 是 create_react_agent 要求的托管字段（递归步数上限）。
    """

    messages: Annotated[list[AnyMessage], add_messages]
    remaining_steps: RemainingSteps
    # API 层注入：本轮按相关性挑选的用户偏好（已格式化）
    user_context: str
    # 上一轮滚动压缩得到的会话摘要
    memory_summary: str


class GraphState(TypedDict, total=False):
    # 对话消息（add_messages 归并：按 id 去重/替换/追加）
    messages: Annotated[list[AnyMessage], add_messages]

    # 会话标识（checkpointer 的 thread 维度由 API 层组装为 u{user}:s{session}）
    user_id: Optional[str]
    session_id: str

    # API 层注入：用户偏好等上下文摘要（拼入 system prompt）
    user_context: str
    # 上一轮滚动压缩得到的会话摘要
    memory_summary: str

    # --- v4 意图路由（生产者=intent_node，消费者=路由条件边/各 fast path 节点）---
    # v0 图不经过 intent_node，以下字段不会被写入
    route: str             # small_talk / faq_answer / agent_execute / clarify / human_transfer
    domain: str            # product / order_logistics / coupon / aftersale / none
    refined_query: str     # intent LLM 提炼的检索问句，faq_answer 时作 search_faq 入参
    clarify_question: str  # route=clarify 时必填（为空则 intent 兜底改道 agent_execute）
    faq_refs: list[dict]   # faq_answer_node 写入，仅用于 checkpoint/Langfuse 观测；
                           # citation 事件由 chat.py 在 on_tool_end 阶段直接透出
