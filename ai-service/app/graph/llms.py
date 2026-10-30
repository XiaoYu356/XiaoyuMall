"""LLM 工厂（v3/v4）：主 Agent 模型 + 意图路由模型。

- 主模型：负责主 Agent 的推理与生成。streaming=True 保证 astream_events 能拿到
  token 级事件（当前 langgraph 版本的模型节点内部走 ainvoke，需靠 streaming
  回调产出 token）。
- v3.1 起 search_faq 的相关性判定由 cross-encoder 重排（app/core/reranker.py）
  替代 CRAG LLM 判级，create_judge_llm 不再存在。
- v4 新增意图模型：轻量结构化任务（function calling），非流式一次产出。
"""
from langchain_openai import ChatOpenAI

from app.core.config import settings


def create_main_llm(temperature: float = 0.7) -> ChatOpenAI:
    """主 Agent 模型（参数与 v2 create_main_llm 一致）。

    enable_thinking=False：DashScope 混合推理模型默认开思考，ReAct 每轮
    （工具调用轮 + 回答轮）都会先输出大量不可见的思考 token，SSE 层拿不到
    内容导致前端长时间空等（TTFT 劣化到分钟级）；客服场景无需深度推理，关闭。
    """
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
        temperature=temperature,
        streaming=True,
        # 自定义 base_url（DashScope）时 langchain-openai 不会自动开启流式用量
        # 上报，需显式传 stream_usage=True 才会在请求中带
        # stream_options.include_usage，流式聚合消息才有 usage_metadata
        # （Langfuse token 统计与 Prometheus llm_tokens_total 均依赖它）
        stream_usage=True,
        extra_body={"enable_thinking": False},
    )


def create_intent_llm(temperature: float = 0.0) -> ChatOpenAI:
    """意图路由模型（v4 轻量结构化任务，走 OPENAI_MODEL_FAST）。

    非流式：with_structured_output（function calling）一次性产出，无需 token
    级事件；enable_thinking=False 同主模型——混合推理模型的思考 token 只会
    拖慢路由决策，分类任务无需深度推理。
    """
    return ChatOpenAI(
        model=settings.OPENAI_MODEL_FAST,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE,
        temperature=temperature,
        extra_body={"enable_thinking": False},
    )
