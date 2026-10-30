"""图装配：v0 单 Agent / v1 意图路由，经 AI_GRAPH_VERSION 切换。

对齐 coupon.receive.version 多版本共存约定：
- v0（默认）：create_react_agent 编译出的 agent ⇄ tools 循环图，一行不改
- v1：手动 StateGraph——START→intent（路由）→ small_talk/faq_answer/clarify/
  human_transfer 直出 END，或 agent⇄tools 完整 ReAct（节点命名对齐 chat.py
  的 SSE 事件过滤）

切换注意：v0/v1 的 state schema 不同（v1 无 remaining_steps 托管字段），
跨版本恢复挂起的 HITL 中断未验证，建议在无 pending interrupt 时切换。
"""
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.graph.nodes.agent import agent_node, create_agent_node, should_continue
from app.graph.nodes.fastpath import (
    clarify_node,
    faq_answer_node,
    human_transfer_node,
    small_talk_node,
)
from app.graph.nodes.intent import intent_node
from app.graph.state import GraphState
from app.tools import ALL_TOOLS

# intent.route → 下游节点名；未知/缺失值兜底 agent（与 intent_node 兜底同向：
# 错进 ReAct 只多花 token，错进快速通道会答错，代价不对称）
_ROUTE_TO_NODE = {
    "small_talk": "small_talk",
    "faq_answer": "faq_answer",
    "agent_execute": "agent",
    "clarify": "clarify",
    "human_transfer": "human_transfer",
}


def _route_pick(state: dict) -> str:
    return _ROUTE_TO_NODE.get(state.get("route") or "", "agent")


def _build_v1_graph(checkpointer):
    """v1 手动装配：intent 前置路由 + fast path 直出 + agent⇄tools 完整循环。

    结构约束：agent⇄tools 循环边只回 agent、永不回 intent（意图每轮只判一次）；
    HITL /resume 从 tools 中断点恢复，天然绕过 intent。
    """
    graph = StateGraph(GraphState)
    graph.add_node("intent", intent_node)
    graph.add_node("small_talk", small_talk_node)
    graph.add_node("faq_answer", faq_answer_node)
    graph.add_node("clarify", clarify_node)
    graph.add_node("human_transfer", human_transfer_node)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    graph.add_edge(START, "intent")
    graph.add_conditional_edges("intent", _route_pick)
    for node in ("small_talk", "faq_answer", "clarify", "human_transfer"):
        graph.add_edge(node, END)
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer)


def build_graph(checkpointer):
    """编译主干图并挂载 checkpointer（thread_id = u{user}:s{session}，API 层组装）。

    注：langgraph 1.x 的 create_react_agent 直接返回已编译的 CompiledStateGraph
    （无 .compile() 方法），checkpointer 经 create_agent_node 透传注入；
    v1 手动图在 _build_v1_graph 内 compile 时注入。
    """
    if settings.AI_GRAPH_VERSION == "v1":
        return _build_v1_graph(checkpointer)
    return create_agent_node(checkpointer)
