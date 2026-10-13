"""v3 主干图装配：单 Agent 节点，START→agent→END。

禁止添加意图分类/快速通道节点——v3 唯一主干就是 create_react_agent 编译出的
agent ⇄ tools 循环图（内部节点名：agent / tools，SSE 层按此过滤事件）。
"""
from app.graph.nodes.agent import create_agent_node


def build_graph(checkpointer):
    """编译主干图并挂载 checkpointer（thread_id = u{user}:s{session}，API 层组装）。

    注：langgraph 1.x 的 create_react_agent 直接返回已编译的 CompiledStateGraph
    （无 .compile() 方法），checkpointer 经 create_agent_node 透传注入。
    """
    return create_agent_node(checkpointer)
