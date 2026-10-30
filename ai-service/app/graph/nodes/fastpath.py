"""fast path 节点（v4）：small_talk / faq_answer / clarify / human_transfer。

与 agent 路径的关系：
- small_talk / clarify / human_transfer 不触碰任何业务工具
- faq_answer 直调 search_faq（不经过 tools 节点）：SSE 的 tool/citation 事件
  由 chat.py 按工具名白名单透出（与 agent 路径同一套解析逻辑）
- 回答模型与主 Agent 同款（create_main_llm，streaming=True 供 llm_chunk 透出），
  快速通道省的是 ReAct 规划轮次，不是生成质量
"""
import json

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.graph.llms import create_main_llm
from app.graph.window import select_recent_messages
from app.tools.faq_tools import search_faq

logger = structlog.get_logger(__name__)

# 回答时携带的最近对话条数（与 intent 窗口一致）
_HISTORY_WINDOW = 4

SMALL_TALK_PROMPT = """你是小鱼商城的智能客服，用户在和你闲聊。
简短友好地回应（一两句即可），并自然引导回购物、订单、优惠券、售后等你
能帮忙的事。不要编造商城政策与活动信息。"""

# refs 文本在节点内 f-string 拼接（避免 .format 与条目内容花括号冲突）
FAQ_ANSWER_PROMPT_HEAD = """你是小鱼商城的客服。仅根据下面给出的知识库条目回答用户问题。

要求：
1. 只能使用条目中的信息，禁止编造条目之外的政策
2. 引用条目内容时在对应句子末尾标注 [n]（n 为条目编号）
3. confidence 为 mid 的条目把握较低，表述留有余地（如"一般""通常"），
   并提示用户以官方说明为准
4. 回答简洁口语化，不要原样复述条目

知识库条目：
"""

_FAQ_EMPTY_ANSWER = "抱歉，商城政策中暂无相关说明。您可以换个问法试试，或联系人工客服获取帮助。"
# 生成环节异常兜底（fast path 卖点是确定性，模型超时/限流不得把整轮打成 error）
_SMALL_TALK_FALLBACK = "抱歉，我这边暂时没能回应上来，请稍后再试。您也可以直接告诉我想查商品、订单还是优惠券。"
_FAQ_GEN_FALLBACK = "抱歉，暂时没能整理出回答，请稍后再试或换个问法重试。"
_DEFAULT_CLARIFY = "抱歉，我没太理解您的需求。您是想查询订单物流、申请售后，还是咨询商品/优惠券呢？"
# 商城暂无在线人工客服接入：不承诺"已记录/正在转接"这类未发生的动作
_HUMAN_TRANSFER_ANSWER = "非常抱歉给您带来了不便。当前在线对话暂不支持直接转接人工客服；您可以继续描述具体问题（涉及商品请提供商品ID或订单号），我会尽力帮您处理。"

_FASTPATH_LLM = None


def _get_fastpath_llm():
    """fast path 回答模型单例（不 bind 工具，省 11 个工具 schema 的上下文开销）。"""
    global _FASTPATH_LLM
    if _FASTPATH_LLM is None:
        _FASTPATH_LLM = create_main_llm()
    return _FASTPATH_LLM


def _last_user_text(messages: list) -> str:
    """最近一条用户消息纯文本（refined_query 缺失时的检索入参兜底）。"""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""


async def small_talk_node(state: dict, config: RunnableConfig) -> dict:
    """闲聊直答：轻人设 prompt + 无工具，一次流式调用（失败退回固定话术）。"""
    messages = [
        SystemMessage(content=SMALL_TALK_PROMPT),
        *select_recent_messages(state["messages"], _HISTORY_WINDOW),
    ]
    try:
        response = await _get_fastpath_llm().ainvoke(messages, config)
    except Exception as e:
        logger.warning("small_talk 生成失败,走兜底话术", error=str(e))
        return {"messages": [AIMessage(content=_SMALL_TALK_FALLBACK)]}
    return {"messages": [response]}


async def faq_answer_node(state: dict, config: RunnableConfig) -> dict:
    """FAQ 快速通道：search_faq 直调 → LLM 组织回答（跳过 ReAct 规划层）。

    refs 为空 → 固定兜底文案（不调 LLM、不重查关键词——快速通道追求确定性
    与低延迟；"换词重查最多 2 次"是 ReAct 路径能力，不迁移）。
    refs 同时写入 state["faq_refs"]：checkpoint/Langfuse trace 中可观测。
    """
    query = state.get("refined_query") or _last_user_text(state["messages"])
    try:
        raw = await search_faq.ainvoke({"query": query}, config)
        payload = json.loads(raw) if isinstance(raw, str) else {}
    except Exception as e:
        logger.warning("faq_answer 检索异常,走兜底话术", error=str(e))
        payload = {}
    refs = payload.get("refs") or []

    if not refs:
        return {"messages": [AIMessage(content=_FAQ_EMPTY_ANSWER)], "faq_refs": []}

    refs_text = "\n".join(
        f"[{r['no']}] {r.get('question', '')}\n{r.get('answer', '')}"
        f"（confidence={r.get('confidence', 'high')}）"
        for r in refs
    )
    messages = [
        SystemMessage(content=FAQ_ANSWER_PROMPT_HEAD + refs_text),
        *select_recent_messages(state["messages"], _HISTORY_WINDOW),
    ]
    try:
        response = await _get_fastpath_llm().ainvoke(messages, config)
    except Exception as e:
        logger.warning("faq_answer 生成失败,走兜底话术", error=str(e))
        return {"messages": [AIMessage(content=_FAQ_GEN_FALLBACK)], "faq_refs": refs}
    return {"messages": [response], "faq_refs": refs}


async def clarify_node(state: dict, config: RunnableConfig) -> dict:
    """0 次 LLM：澄清问题已由 intent_node 一次产出，直接包装为 AIMessage。

    clarify_question 理论必经 intent_node 非空校验，此处仍防御性给默认句
    （兜底条件要宽：任何路径都不能产出空回复）。
    """
    question = (state.get("clarify_question") or "").strip() or _DEFAULT_CLARIFY
    return {"messages": [AIMessage(content=question)]}


async def human_transfer_node(state: dict, config: RunnableConfig) -> dict:
    """0 次 LLM：固定安抚话术（不承诺系统未实现的转接/记录动作）。"""
    return {"messages": [AIMessage(content=_HUMAN_TRANSFER_ANSWER)]}
