"""主 Agent 节点（v4：v0 图整体编译，v1 图复用下方 agent_node / should_continue）。

两个版本共用同一份模型、提示词与上下文治理逻辑：
- v0（AI_GRAPH_VERSION=v0，默认）：create_agent_node 编译 create_react_agent，
  agent ⇄ tools 循环即整张图，无意图分类、无快速通道
- v1（AI_GRAPH_VERSION=v1）：builder 手动装配 StateGraph，本模块的 agent_node 与
  should_continue 承担 ReAct 主干，入口前置 intent 路由 + 四条 fast path 直出
  （见 app/graph/nodes/fastpath.py）；agent⇄tools 循环边不回 intent

设计要点（自 v2 main_agent.py 迁移，agentic RAG 版）：
- 单主 Agent 而非按域拆分专家 Agent：减少 LLM 调用次数、保持完整上下文，
  模型可在一次规划中并行调用多个无依赖工具
- search_faq 与其他业务工具同级注册，模型自主决定是否检索知识库（agentic RAG）；
  相关性判定在工具内完成（三路召回 + cross-encoder 精排 + 置信度阈值分级，
  见 app/core/reranker.py），refs 为空时模型走"如实告知"兜底，回答带 [n] 引用
- 写操作（售后域）由工具内 LangGraph interrupt 硬中断兜底
- pre_model_hook 做四件事：trim 上下文封顶 token 成本 + 旧工具结果 masking +
  注入滚动摘要/top-k 用户偏好；返回 llm_input_messages 仅覆盖本次模型输入，
  checkpoint state 不动，保证 interrupt/resume 与完整轨迹不受影响
- 摘要与偏好都在 trim 之后注入：trim_messages(start_on="human") 会把窗口头部
  的 SystemMessage 丢掉，先注入偏好再裁剪会导致每轮偏好消失（首轮尤其明显）
"""
from typing import Any, List

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.messages.utils import trim_messages
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END
from langgraph.prebuilt import create_react_agent
import tiktoken

from app.graph.llms import create_main_llm
from app.graph.state import AgentGraphState
from app.tools import ALL_TOOLS

# tiktoken encoding：deepseek 系列兼容 cl100k_base
# 模块级加载一次，避免 _count_msg_tokens 逐条调用时重复加载编码表
_ENC = tiktoken.get_encoding("cl100k_base")

# OpenAI chat format 每条消息的 role 框架开销（tokens_per_message=3）
# 参考 https://platform.openai.com/docs/guides/text-generation/managing-tokens
_ROLE_OVERHEAD = 3

# 模型上下文预算（真实 cl100k token），预算 10000 约等于 15~20 轮正常客服对话
# deepseek-v4.1-flash 长上下文 + 低价，此预算主要作为"用户长期不点清空"的成本保险
# 换 approximate 会对中文严重低估（6000 approximate ≈ 24000 真实 token），
# 改用 tiktoken cl100k_base 精确计数
CONTEXT_TOKEN_BUDGET = 10000

# 摘要/偏好注入后的最小可用窗口（防止额外上下文把消息窗口挤到 0）
MIN_CONTEXT_TOKEN_BUDGET = 2000

# 旧工具结果 masking：只保留最近 N 条 ToolMessage 原文，更早的替换为占位符。
# 这类结果大多可重新查询（商品/订单/FAQ），比整段丢弃更省 token 且不丢"调用过"的事实
KEEP_RECENT_TOOL_RESULTS = 4
MASK_MIN_CHARS = 200
TOOL_PLACEHOLDER = "[工具 {name} 的早期返回已省略以节省上下文；如仍需这些数据请重新调用该工具]"

# chat.py 每轮请求注入的偏好 SystemMessage 前缀，用于兼容清理历史遗留消息
_PREFERENCE_MSG_PREFIX = "[用户偏好] "
_SUMMARY_MSG_PREFIX = "[历史摘要] "

# 系统提示词：v2 十条工作规则原样迁移 + v3 新增三条（11~13）
SYSTEM_PROMPT = """你是小鱼商城的智能客服与购物助手，直接调用工具完成用户请求，禁止编造实时数据。

工作规则：
1. 涉及商品、价格、库存、优惠券、物流、订单等实时数据时，必须先调用工具查询，禁止凭记忆回答
2. 相互无依赖的工具可以在一次规划中并行调用（例如同时查多个商品、或查商品详情+可用优惠券）
3. 工具返回的是结构化文本，请整理成简洁自然的中文回答，金额保留两位小数
4. 回答中提到具体商品时，在回答末尾单独一行输出"商品ID:<id>"（前端依赖该格式渲染商品卡片）
5. 查询失败或数据不存在时如实告知，不臆测
6. 回答简短友好，不重复用户问题
7. 用户询问"我的订单""我买了什么""我的优惠券"等自身数据时，直接调用对应工具查询，
   不要向用户索要用户ID（系统已知当前登录用户）
8. 售后写操作由系统强制执行人工确认（无需你征求确认）：
   a) 用户明确表达退款/退货意愿时，直接调用 submit_aftersale；系统会自动暂停
      并向用户展示确认卡片，用户点击确认后才真正执行
   b) 若用户取消，工具会返回"用户已取消"，如实转告即可，不要重复发起
   c) 退货退款审核通过后告知寄回；用户表示已寄回后调用 complete_return_refund，
      同样由系统自动向用户确认
9. 用户问物流/货到哪了，先查订单拿到订单号，再调用 get_logistics_timeline
10. 用户情绪激动或明确要求人工客服时，先安抚，并告知正在为其转接人工
11.凡涉及商城政策、规则、费用、流程类问题（售后/退款/发货/优惠券规则/积分规则/账号问题/会员权益等），**必须优先调用 search_faq** 并以知识库内容为准，禁止凭训练数据臆测政策；search_faq 已内置 cross-encoder 精排与置信度分级：refs 为空可换关键词重查（最多 2 次），仍为空则如实告知"商城政策中暂无相关说明"并建议联系人工客服，绝不编造政策；confidence 为 mid 的条目把握较低，表述留有余地并建议用户以官方说明为准
12. 回答引用知识库条目时，在对应句子末尾标注 [n]（n 为 refs 里的编号）
13. 工具返回 JSON 时（如 search_products 的 products、search_faq 的 refs），
    直接读取字段内容组织回答，不要原样复述 JSON
14. 调用工具前，先用一句简短中文说明你要做什么（如"我先查一下退货政策""我来帮您
    查询订单"），再发起工具调用，让用户能实时看到处理进度；说明要口语化、简短，
    不要罗列步骤"""


def _count_msg_tokens(msg: BaseMessage) -> int:
    """单消息真实 token 计数（cl100k_base）。

    trim_messages 的 token_counter 接收单消息 callable 时会逐条调用并累加；
    这里对齐 OpenAI chat format：每条 role 框架 3 token + content token + 额外字段。
    deepseek 系列兼容 cl100k_base，对中文偏差 <10%。
    """
    n = _ROLE_OVERHEAD
    # content token
    if msg.content:
        n += len(_ENC.encode(msg.content if isinstance(msg.content, str) else str(msg.content)))
    # AIMessage.tool_calls 序列化 token（工具调用时模型传的参数 schema）
    if isinstance(msg, AIMessage) and msg.tool_calls:
        n += len(_ENC.encode(str(msg.tool_calls)))
    # ToolMessage.tool_call_id（每条 3 token，同 langchain_openai 计数）
    if isinstance(msg, ToolMessage) and msg.tool_call_id:
        n += 3
    return n


def _count_text_tokens(text: str) -> int:
    """纯文本 token 计数（含 1 条消息的 role 框架开销）。"""
    return _ROLE_OVERHEAD + len(_ENC.encode(text)) if text else 0


def _content_text(content: Any) -> str:
    """消息 content → 纯文本（兼容多模态块列表）。"""
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


def split_for_model(
    messages: List[BaseMessage], max_tokens: int = CONTEXT_TOKEN_BUDGET
) -> tuple[List[BaseMessage], List[BaseMessage]]:
    """按模型预算切分消息：返回 (保留窗口, 被裁剪的旧消息)。

    裁剪规则与线上完全一致（last + start_on='human' + cl100k_base 计数），
    供 pre_model_hook 与摘要模块共用，避免两处口径漂移。
    """
    messages = list(messages)
    trimmed = trim_messages(
        messages,
        max_tokens=max_tokens,
        token_counter=_count_msg_tokens,
        strategy="last",
        include_system=False,
        start_on="human",
    )
    dropped_count = max(0, len(messages) - len(trimmed))
    return trimmed, messages[:dropped_count]


def _mask_stale_tool_results(messages: List[BaseMessage]) -> List[BaseMessage]:
    """旧工具结果 masking：保留最近 N 条 ToolMessage 原文，更早的换占位符。

    只改本次模型输入（副本），checkpoint 里的原始工具输出保持完整，
    因此前端历史、审计、重新追问都不受影响；模型若需要旧数据可重新调用工具。
    """
    tool_indexes = [
        i for i, msg in enumerate(messages) if isinstance(msg, ToolMessage)
    ]
    stale = tool_indexes[: max(0, len(tool_indexes) - KEEP_RECENT_TOOL_RESULTS)]
    if not stale:
        return messages

    result = list(messages)
    for i in stale:
        msg = result[i]
        text = _content_text(msg.content)
        if len(text) <= MASK_MIN_CHARS:
            continue
        name = getattr(msg, "name", None) or "结果"
        result[i] = msg.model_copy(
            update={"content": TOOL_PLACEHOLDER.format(name=name)}
        )
    return result


def _dedupe_legacy_preference_messages(
    messages: List[BaseMessage],
) -> List[BaseMessage]:
    """清掉历史遗留的多份 [用户偏好] SystemMessage，只留最后一份。

    新版偏好不再写入 messages（由 _pre_model_trim 动态注入），
    这里仅兼容旧会话 checkpoint 里已经攒下的注入消息。
    """
    last_idx = -1
    for i, msg in enumerate(messages):
        if isinstance(msg, SystemMessage) and msg.content.startswith(
            _PREFERENCE_MSG_PREFIX
        ):
            last_idx = i
    if last_idx <= 0:
        return messages
    return [
        msg for i, msg in enumerate(messages)
        if i == last_idx
        or not (
            isinstance(msg, SystemMessage)
            and msg.content.startswith(_PREFERENCE_MSG_PREFIX)
        )
    ]


def _pre_model_trim(state: dict) -> dict:
    """模型调用前组装输入：裁剪 → masking → 去重 → 注入摘要/偏好。

    只返回 llm_input_messages 覆盖本次模型输入，checkpoint state 不动：
    - checkpoint 保持全量历史 → interrupt/resume 依赖的 AI(tool_calls)→Tool 配对完整
    - 摘要/偏好在裁剪之后注入，避免被 start_on='human' 的窗口对齐丢掉
    - 不设 include_system=True，SYSTEM_PROMPT 由 create_react_agent 的 prompt 独立注入
    """
    messages = list(state["messages"])
    summary = (state.get("memory_summary") or "").strip()
    preferences = (state.get("user_context") or "").strip()

    # 动态注入的上下文也要占预算，否则实际请求会超出 CONTEXT_TOKEN_BUDGET
    extra_tokens = _count_text_tokens(f"{_SUMMARY_MSG_PREFIX}{summary}") if summary else 0
    extra_tokens += (
        _count_text_tokens(f"{_PREFERENCE_MSG_PREFIX}{preferences}") if preferences else 0
    )
    budget = max(CONTEXT_TOKEN_BUDGET - extra_tokens, MIN_CONTEXT_TOKEN_BUDGET)

    trimmed, _dropped = split_for_model(messages, max_tokens=budget)
    trimmed = _mask_stale_tool_results(trimmed)
    trimmed = _dedupe_legacy_preference_messages(trimmed)

    prefix: List[BaseMessage] = []
    if summary:
        prefix.append(SystemMessage(content=f"{_SUMMARY_MSG_PREFIX}{summary}"))
    if preferences:
        prefix.append(SystemMessage(content=f"{_PREFERENCE_MSG_PREFIX}{preferences}"))

    return {"llm_input_messages": [*prefix, *trimmed]}


def create_agent_node(checkpointer=None):
    """构建单 Agent 主干图并挂载 checkpointer。

    注：langgraph 1.x 的 create_react_agent 返回的是已编译的 CompiledStateGraph
    （内部结构 START → agent ⇄ tools → END，无 .compile() 方法），
    checkpointer 经其同名参数注入。
    """
    return create_react_agent(
        create_main_llm(),
        ALL_TOOLS,
        prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
        pre_model_hook=_pre_model_trim,
        state_schema=AgentGraphState,
    )


# ---------------------------------------------------------------------------
# v4 手动 ReAct 节点（AI_GRAPH_VERSION=v1 时由 builder 装配）
# 节点命名必须保持 agent/tools：chat.py 的 SSE 事件过滤（node=="agent"/"tools"）、
# tool 事件、citation/product_card 解析逻辑依赖该命名，对齐后零改动
# ---------------------------------------------------------------------------

_AGENT_TOOLS_LLM = None


def _get_agent_llm():
    """bind_tools 后的主模型单例（模块级懒加载，避免节点内重复绑定）。"""
    global _AGENT_TOOLS_LLM
    if _AGENT_TOOLS_LLM is None:
        _AGENT_TOOLS_LLM = create_main_llm().bind_tools(ALL_TOOLS)
    return _AGENT_TOOLS_LLM


async def agent_node(state: dict, config: RunnableConfig) -> dict:
    """v4 agent 节点：trim 上下文 → 前置 system prompt → 调模型。

    与 create_react_agent 内部模型节点逐项对齐：
    - _pre_model_trim 原样复用（只覆盖本次模型输入，checkpoint state 不动，
      interrupt/resume 依赖的 AI(tool_calls)→Tool 配对完整）
    - SYSTEM_PROMPT 每次调用注入（等价 create_react_agent 的 prompt 参数）
    - config 透传（Langfuse callback、recursion_limit 生效）
    """
    trimmed = _pre_model_trim(state)["llm_input_messages"]
    messages = [SystemMessage(content=SYSTEM_PROMPT), *trimmed]
    response = await _get_agent_llm().ainvoke(messages, config)
    return {"messages": [response]}


def should_continue(state: dict) -> str:
    """agent → tools/END 条件边：末条 AI 消息带 tool_calls 则进工具循环。"""
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return END
