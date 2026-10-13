# Tasks — AI 客服 v3 重构（P0+P1）

所有新代码位于 `ai-service/app/`。实施期间 v2 代码（`main.py`/`graph/`/`agents/`/`core/`/`config/`/`api/`）**只读参照，不做任何修改**；Task 6 端到端验收全部通过后按 Task 7 物理删除。启动方式：cwd=`ai-service`，`ai-service\.venv\Scripts\python.exe -m app.main`。所有模块 import 用 `app.` 前缀绝对导入。注意历史教训：Python 文件禁止 BOM（历史曾因 12 组 U+FEFF 导致 SyntaxError）。

- [x] Task 1: P0 骨架与横切层（core 四件 + audit + main + health）
  - [x] 1.1 `app/__init__.py`、`app/core/__init__.py`、`app/core/config.py`：pydantic-settings；变量名与 v2 `config/settings.py` 保持一致（REDIS_*/OPENAI_*/服务 URL/INTERNAL_SECRET/MYSQL_*/MEMORY_MAX_TURNS，env_file=".env"，case_sensitive=True），新增 v3 专属：LANGFUSE_PUBLIC_KEY/SECRET_KEY/HOST（默认空=禁用）、RATE_LIMIT_USER_PER_MIN=20、RATE_LIMIT_GLOBAL_QPS=200、SSE_MAX_CONN_PER_USER=3、INPUT_MAX_CHARS=2000、LOG_LEVEL=INFO、SERVICE_BASE_URL（拼 trace_url 用）
  - [x] 1.2 `app/core/observability.py`：structlog JSON 配置（contextvars 携带 request_id）；prometheus-client 指标注册表（sse_requests_total、ttft_seconds、e2e_latency_seconds{served_by}、tool_calls_total{tool,ok}、tool_latency_seconds{tool}、llm_tokens_total{type}、rate_limited_total、sse_active_connections）；`build_langfuse_callback()`：未配 key 返回 None，配置了返回 `langfuse.langchain.CallbackHandler`（langfuse v2 SDK）
  - [x] 1.3 `app/core/http_client.py`：lifespan 创建/关闭共享 `httpx.AsyncClient`；`request_internal(method, url, *, params=None, json=None, timeout=3.0)` 自动带 `X-Internal-Secret`；仅对 `httpx.TransportError`（连接未建立）重试 1 次；失败抛 `UpstreamError(message)`；提供 `get_http_client()`
  - [x] 1.4 `app/core/security.py`：FastAPI 依赖 `get_request_user(request)`（X-User-Id 头优先 → user_id query 回退 → 401）；`check_rate_limit(redis, user_id)`（ZSET 滑动窗口 per-user + INCR 固定窗口全局，超限 429）；`acquire_sse_slot/release_sse_slot`（INCR/DECR + TTL 兜底，超 3 拒绝）；`sanitize_input(q)`（截断 2000）与 `detect_injection(q)`（规则列表：忽略(之前|以上|上面的)(所有)?指令/ignore (all )?previous/system prompt/jailbreak/你现在是(管理员|系统|开发者模式)/DAN mode，命中返回 True）
  - [x] 1.5 `app/core/audit.py`：整体迁移 v2 `core/audit.py`（pymysql + asyncio.to_thread + best-effort），仅改 import 为 `app.core.config`
  - [x] 1.6 `app/api/__init__.py`、`app/api/health.py`（`/api/v3/health`：status/version/checkpointer 模式；`/metrics`：prometheus generate_latest）+ `app/main.py`（lifespan：init_checkpointer → build_graph 存 app.state → http client 建立与关闭；CORS；挂路由；`__main__` 用 uvicorn.run("app.main:app")）
  - [x] 1.7 `requirements.txt` 追加：langfuse==2.60.5、prometheus_client==0.23.1、structlog==25.5.0（structlog 25.6.0 不存在，按放宽策略取 25.5.0）
  - 验证：`python -m app.main` 启动无报错；`GET /api/v3/health` 200（checkpointer=redis，graph=not_assembled）；`GET /metrics` 非空
  - 备注：为使 P0 自洽，`app/graph/__init__.py` + `app/graph/checkpointer.py`（含 checkpointer_mode()）提前至 Task 1 完成；2.1 中 checkpointer 部分相应勾销

- [x] Task 2: 图与五域工具（P1 核心）
  - [x] 2.1 `app/graph/__init__.py`、`app/graph/state.py`（GraphState：messages(add_messages)/user_id/session_id/user_context，无任何 intent 字段）+ ~~checkpointer~~（已提前至 Task 1 完成）
  - [x] 2.2 `app/core/embeddings.py`（迁移 v2 `graph/embeddings.py`：qwen3.7-text-embedding-flash、1024 维、10 条分批）+ `app/core/es_client.py`（迁移并扩展 v2 `graph/es_client.py`：新增 `FAQ_INDEX_V3="mall_faq_v3"` 与 §13.2 mapping（question/similar_questions 用 ik_max_word 索引 + ik_smart 搜索、answer enabled:false、question_vector knn cosine 1024、category/tags keyword、version integer、settings 含自定义 ik_smart_a 分析器）；`search_faq_v3(query, query_vector, top_k=3)` 三路并行召回 top10 → RRF(k=60) top3，返回 `[{id,question,answer,category,score}]`；保留商品搜索函数）
  - [x] 2.3 `app/tools/__init__.py` + 五域工具（每域一文件；模式：`@tool` + `config: RunnableConfig` 注入 user_id/session_id（`_current_user_id/_current_session_id` 助手放 `app/tools/base.py`）+ 经 `app.core.http_client.request_internal` 调 Java + 可读错误文本 + 耗时/成败打点）：
    - `product_tools.py`：`search_products`（GET product-service /api/v1/products，返回 JSON 字符串 `{"products":[{id,name,price,original_price,sales,image}]}`，供 SSE 层出 product_card）、`get_product_detail`（返回含单商品 JSON + 规格文本）
    - `coupon_tools.py`：`get_available_coupons`、`calculate_coupon_discount`、`get_my_coupons`（迁移 v2 两处实现，含领券中心库存/过期过滤逻辑）
    - `order_tools.py`：`get_my_orders`、`get_order_detail`（保留越权双保险）、`get_logistics_timeline`
    - `aftersale_tools.py`：`submit_aftersale`、`complete_return_refund`（迁移 v2 interrupt 模式：interrupt 前只读幂等校验；payload 含 action/order_no/items/type_text/refund_amount/reason；approved 后执行写接口并 `app.core.audit.write_audit` success/rejected/failed 三态）
    - `faq_tools.py`：`search_faq(query)`——描述写明边界（政策/规则/费用/流程类才用；实时数据勿用）与重查策略（最多 2 次换关键词）；实现：`embed_text(query)` → `es_client.search_faq_v3` → 返回 JSON `{"refs":[{"no":1,"question":...,"answer":...,"score":...,"category":...}]}`（score 原样透传，不卡阈值）
  - [x] 2.4 `app/graph/nodes/__init__.py`、`app/graph/nodes/agent.py`（系统提示词：迁移 v2 十条规则 + 新增：search_faq 结果 score 低则换问法重查或如实说不知道、回答引用 [n]、工具 JSON 结构说明）+ `app/graph/builder.py`（单节点 agent 图，START→agent→END）
  - 验证：compileall 全过；ALL_TOOLS=11；图编译成功（nodes: __start__/agent/tools/__end__，mode:redis）；Java 服务直调冒烟通过；v2 零改动
  - 备注：langgraph 1.2.12 的 `create_react_agent` 直接返回已编译图，builder 以 `create_agent_node(checkpointer)` 注入 checkpointer（与原计划的 build_graph(checkpointer) 等价，以实际代码为准）；`timed_call` 显式放行 `GraphBubbleUp`（保证 interrupt 不被兜底异常吞掉）

- [x] Task 3: API 层（SSE v3 + resume + feedback + memory 兼容）
  - [x] 3.1 `app/api/chat.py`：GET /api/v3/chat/stream 全流程实现（安全门→meta→astream_events 翻译→interrupt 检测（StateSnapshot.interrupts，dataclass 取 .value）→历史/整理→complete；异常 error+complete）。实测：meta→tool(start/end elapsed_ms)→product_card(4 商品)→llm_chunk×65→complete(usage 4771/403/12145ms)
  - [x] 3.2 `app/api/resume.py`：POST /api/v3/resume 幂等（redis.set nx=True falsy 判断）、StateSnapshot 读 pending、Command(resume) 恢复、身份 get_request_user 优先
  - [x] 3.3 `app/api/feedback.py` + `scripts/sql/v3_feedback.sql`
  - [x] 3.4 `app/api/memory.py`：四个兼容端点与 AIController 代理路径/响应逐字段一致，挂载 /api/v1/ai 前缀
  - 验证：SSE 实测全事件序列、注入降级（日志含 injection_blocked+request_id）、401、/metrics 有样本、health graph=ready、memory 端点 200 对齐
  - 备注：structlog BoundLogger.warning 首参即 event，不能重复传 event= kwarg

- [x] Task 4: 记忆闭环
  - [x] 4.1 `app/memory/__init__.py`（get_redis()/close_redis() 共享单例）、`app/memory/profile.py`（偏好 hash 读写，键与 v2 一致）+ `app/memory/history.py`（会话 list：add_message/get_history/clear_session，TTL 与裁剪同 v2）
  - [x] 4.2 `app/memory/consolidator.py`：迁移 v2 逻辑，游标改 Redis：`maybe_consolidate(user_id, session_id)`——`LLEN(chat) - GET(memcur:{u}:{s})` 差值 ≥4 时 `SET memlock:{u}:{s} NX EX 60` 抢锁 → SET 游标 → 后台 task LLM 结构化提取（UserPreferences，json_mode）→ 覆盖写偏好；无进程内游标；main.py lifespan 追加 close_redis()
  - 验证：临时脚本实测全过（偏好写入读回、4 条历史、memcur=4 且锁存在、LLM 成功提取偏好、二次调用差值 0 不触发）；v2 零改动

- [x] Task 5: FAQ 知识库 v3 构建
  - [x] 5.1 `scripts/build_faq_index.py`（`python -m scripts.build_faq_index`）：19 条种子 LLM 全部成功生成 similar_questions（0 兜底）、embed、ensure_faq_index_v3(recreate=True)、bulk 19 条、alias mall_faq 原子切换（含 v2 遗留同名实体索引一次性让路删除）
  - 验证：两次构建幂等（_count=19 不变、top3 与 RRF 分一致）；冒烟「退货政策」top3 全部命中售后类且带 score；search_faq 工具直调返回 refs/score
  - 备注：ES text 字段不支持 enabled:false，answer 改为等价 index:false；bulk 契约不含 id，ES _id 自动生成

- [x] Task 6: 端到端验收（对照 checklist.md 全项）
  - [x] 6.1 启动/健康/metrics（health graph=ready、checkpointer=redis、/metrics 有样本）
  - [x] 6.2 SSE 心跳与全事件序列（含 product_card 4 商品、citation refs+[1][2][3] 引用）
  - [x] 6.3 HITL：interrupt 事件（action/payload/resume_token）→ resume 确认（RMA202610100038468775A2，审计 success）/取消（审计 rejected）/重复（409 ALREADY_PROCESSED）
  - [x] 6.4 审计与反馈落库（ai_action_audit id=7 rejected、id=8 success；ai_chat_feedback 建表后落库 1 行完整）
  - [x] 6.5 限流 429（第 21 次，HTTP 层复验 17×429，rate_limited_total 增长）/ 注入降级 / 超长截断（2718 字符正常）
  - [x] 6.6 v2 参照完整性核查（mtime ≤ 2026-10-09 15:08，会话内零改动）

- [x] Task 7: 删除 v2 旧代码（前置条件：Task 6 全部通过）
  - [x] 7.1 删除 v2 入口与链路：`ai-service/main.py`、`graph/`、`agents/`、`core/`、`config/`、`api/` 整目录
  - [x] 7.2 审查并删除 `scripts/` 下 v2 专属脚本（import_faq.py/eval_intent.py/golden_set.py 均核实为 v2 依赖后删除）；删除旧 demo 页 `static/`；删除杂散旧虚拟环境 `venv/`；**保留** `scripts/faq_seed.py`、`requirements.txt`、`.venv/`、`.env`；另清理陈旧 v2 引用：`tests/test_streaming.py`（打已删 v1 端点）、`docs/streaming*.md`（描述已删 v2 模块）、README 重写为 v3 实况
  - [x] 7.3 删除后验证：残留 import 扫描 0 命中；compileall 全过；`python -m app.main` 启动冒烟（health 200 graph=ready + SSE meta→llm_chunk×34→complete）；项目记忆启动命令已更新

# Task Dependencies
- Task 1 → Task 2（config/http_client/audit 被工具依赖）→ Task 3（chat 依赖图与工具）；Task 4 仅依赖 Task 1，可与 Task 2/3 并行；Task 5 依赖 2.2（es_client/embeddings），可与 Task 3/4 并行；Task 6 最后；Task 7 依赖 Task 6 全部通过。
