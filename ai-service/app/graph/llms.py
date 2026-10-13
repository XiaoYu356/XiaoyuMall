"""LLM 工厂（v3）：仅主 Agent 所需。

- 主模型：负责主 Agent 的推理与生成。streaming=True 保证 astream_events 能拿到
  token 级事件（当前 langgraph 版本的模型节点内部走 ainvoke，需靠 streaming
  回调产出 token）。
- v3.1 起 search_faq 的相关性判定由 cross-encoder 重排（app/core/reranker.py）
  替代 CRAG LLM 判级，create_judge_llm 不再存在。
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
        extra_body={"enable_thinking": False},
    )
