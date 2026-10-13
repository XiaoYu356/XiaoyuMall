"""主 Agent 节点（v3 唯一节点）：create_react_agent 挂载五域全部 11 工具。

设计要点（自 v2 main_agent.py 迁移，agentic RAG 版）：
- 单主 Agent 而非按域拆分专家 Agent：减少 LLM 调用次数、保持完整上下文，
  模型可在一次规划中并行调用多个无依赖工具
- search_faq 与其他业务工具同级注册，模型自主决定是否检索知识库（agentic RAG）；
  相关性判级（CRAG）在 search_faq 工具内完成：工具内 LLM 过滤掉与问题不符的
  召回条目（域外 query 会拿到高分错误条目，score 透传自检挡不住），refs 为空
  时模型走"如实告知"兜底，回答带 [n] 引用
- 写操作（售后域）由工具内 LangGraph interrupt 硬中断兜底
- 无意图分类节点、无快速通道：v3 唯一主干就是本节点
- pre_model_hook 做两件事：trim 上下文封顶 token 成本 + 偏好去重；
  返回 llm_input_messages 仅覆盖本次模型输入，checkpoint state 不动，
  保证 interrupt/resume 与完整轨迹不受影响
"""
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.messages.utils import trim_messages
from langgraph.prebuilt import create_react_agent
import tiktoken

from app.graph.llms import create_main_llm
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

# chat.py 每轮请求注入的偏好 SystemMessage 前缀，用于 trim 后去重
_PREFERENCE_MSG_PREFIX = "[用户偏好] "

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


def _pre_model_trim(state: dict) -> dict:
    """模型调用前裁剪上下文 + 偏好去重。

    只返回 llm_input_messages 覆盖本次模型输入，checkpoint state 不动：
    - checkpoint 保持全量历史 → interrupt/resume 依赖的 AI(tool_calls)→Tool 配对完整
    - trim 失败或异常不影响主流程（LangGraph 框架容错）

    两步顺序：先 trim 再去重（trim 产出更小列表，去重更快；且去重只删 SystemMessage
    不影响 start_on='human' 窗口起点合法性）。不设 include_system=True，因为
    SYSTEM_PROMPT 由 create_react_agent 的 prompt 参数独立注入，不在 state['messages'] 里。
    """
    messages = state["messages"]

    # 1) token 预算内的滑动窗口裁剪（自定义 cl100k_base 计数，适配 deepseek 系列）
    trimmed = trim_messages(
        messages,
        max_tokens=CONTEXT_TOKEN_BUDGET,
        token_counter=_count_msg_tokens,
        strategy="last",
        include_system=False,
        start_on="human",
    )

    # 2) trim 后窗口内可能残留多份 [用户偏好] SystemMessage（每轮注入一份），
    #    只保留最后一份（最新偏好），前面的全部过滤掉，避免浪费窗口预算
    last_pref_idx = -1
    for i, msg in enumerate(trimmed):
        if (
            isinstance(msg, SystemMessage)
            and msg.content.startswith(_PREFERENCE_MSG_PREFIX)
        ):
            last_pref_idx = i
    if last_pref_idx > 0:
        trimmed = [
            m for i, m in enumerate(trimmed)
            if i == last_pref_idx  # 保留最后一份偏好
            or not (
                isinstance(m, SystemMessage)
                and m.content.startswith(_PREFERENCE_MSG_PREFIX)
            )
        ]

    return {"llm_input_messages": trimmed}


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
    )
