"""意图路由节点（v4）：一次轻量 LLM 调用产出 route/domain/refined_query/clarify_question。

设计要点：
- OPENAI_MODEL_FAST + with_structured_output（function calling）保证 JSON 格式稳定
- 输入最近 4 条消息（覆盖两轮对话，解决"那退货呢"这类多轮指代）
- 三层兜底全部偏向 agent_execute：错进 ReAct 只多花 token，错进快速通道会答错
  （代价不对称），且任何路径都不允许空回复到达用户
- 每轮请求入口执行一次：图结构上 agent⇄tools 循环边永远不回 intent，
  HITL /resume 从 tools 中断点恢复也天然绕过本节点
"""
import time
from typing import Literal, Optional

import structlog
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.core.observability import intent_latency_seconds, intent_routes_total
from app.graph.llms import create_intent_llm
from app.graph.window import select_recent_messages

logger = structlog.get_logger(__name__)

# intent 看到的最近对话条数（两轮问答，兼顾指代消歧与 prompt 长度）
_HISTORY_WINDOW = 4

INTENT_PROMPT = """你是电商客服的意图路由器。根据最近对话，判断用户最新一条消息该走哪条处理链路。

路由规则（按优先级从高到低）：
1. human_transfer：用户情绪激动、辱骂，或明确要求人工客服
2. agent_execute：满足任一条件必须选它——
   a) 涉及具体商品（商品名、商品ID、"这个/那件"等指向具体商品的表述）
   b) 涉及"我的"数据：我的订单、我的优惠券、我的物流、我买了什么
   c) 需要实时数据：价格、库存、可用优惠券、订单状态、物流进度
   d) 既问政策又涉及具体实体（如"这个商品能退吗"）
   e) 售后办理：要退款、要退货、表示已寄回
   f) 多步或复合诉求（如"查商品顺便看看有啥券"）
3. faq_answer：纯平台政策/规则/流程/费用咨询，不涉及任何具体实体与"我的"数据
   （如"七天无理由退货条件""优惠券过期能续吗""积分怎么获取"），
   并在 refined_query 给出检索提炼版问句（保留关键数字与名词）
4. small_talk：打招呼、寒暄、无业务诉求
5. clarify：指代不明、无法判断诉求（如"我那个东西咋回事"），
   并在 clarify_question 给出一句口语化反问（提供 2-3 个明确选项，
   如"你是想查订单物流、申请售后，还是咨询其他问题呢？"）

兜底原则：拿不准一律 agent_execute（宁可多花成本，不可答错）。"""


class IntentResult(BaseModel):
    """意图路由结构化输出（function calling schema）。"""

    route: Literal[
        "small_talk", "faq_answer", "agent_execute", "clarify", "human_transfer"
    ] = Field(description="路由决策，取值含义见系统提示词")
    domain: Literal["product", "order_logistics", "coupon", "aftersale", "none"] = Field(
        default="none",
        description="业务域，仅 route=agent_execute 时有意义，其余填 none",
    )
    refined_query: str = Field(
        default="", description="route=faq_answer 时必填：检索提炼版问句"
    )
    clarify_question: str = Field(
        default="", description="route=clarify 时必填：口语化反问，含 2-3 个明确选项"
    )


_INTENT_LLM = None


def _get_intent_llm():
    """with_structured_output 包装单例（模块级懒加载）。"""
    global _INTENT_LLM
    if _INTENT_LLM is None:
        _INTENT_LLM = create_intent_llm().with_structured_output(IntentResult)
    return _INTENT_LLM


def _fallback() -> dict:
    return {
        "route": "agent_execute",
        "domain": "none",
        "refined_query": "",
        "clarify_question": "",
    }


def _record(decision: dict, started: Optional[float] = None) -> dict:
    """记录路由决策指标（route 分布 + intent 耗时）后原样返回决策。

    兜底改道同样计入：agent_execute 的计数偏高即提示 intent 稳定性问题。
    """
    route = decision.get("route") or "agent_execute"
    intent_routes_total.labels(route=route).inc()
    if started is not None:
        intent_latency_seconds.labels(route=route).observe(
            time.perf_counter() - started
        )
    return decision


async def intent_node(state: dict, config: RunnableConfig) -> dict:
    """意图路由：轻量 LLM 一次调用，三层兜底全部偏向 agent_execute。

    1. 无消息 / LLM 异常 → agent_execute
    2. structured output 解析结果类型异常 → agent_execute
    3. route=clarify 但 clarify_question 为空/非字符串 → 改道 agent_execute
    """
    history = select_recent_messages(state.get("messages") or [], _HISTORY_WINDOW)
    if not history:
        return _record(_fallback())
    started = time.perf_counter()
    try:
        result = await _get_intent_llm().ainvoke(
            [SystemMessage(content=INTENT_PROMPT), *history],
            config,
        )
    except Exception as e:
        logger.warning("intent_node 调用失败,兜底 agent_execute", error=str(e))
        return _record(_fallback(), started)
    if not isinstance(result, IntentResult):
        logger.warning(
            "intent_node 解析异常,兜底 agent_execute", got=type(result).__name__
        )
        return _record(_fallback(), started)
    if result.route == "clarify" and not (
        isinstance(result.clarify_question, str) and result.clarify_question.strip()
    ):
        logger.warning("intent_node clarify 反问为空,改道 agent_execute")
        return _record(_fallback(), started)
    logger.info("intent_node 路由", route=result.route, domain=result.domain)
    return _record(
        {
            "route": result.route,
            "domain": result.domain,
            "refined_query": result.refined_query.strip(),
            "clarify_question": result.clarify_question.strip(),
        },
        started,
    )
