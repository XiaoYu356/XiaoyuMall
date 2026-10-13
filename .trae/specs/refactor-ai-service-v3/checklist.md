# Checklist — AI 客服 v3 重构（P0+P1）

## P0 骨架与契约
- [x] `ai-service/app/` 全部模块以 `python -m app.main`（cwd=ai-service，.venv）启动无 import 错误（含无 BOM；compileall 全过 + 服务实际启动）
- [x] `GET /api/v3/health` 返回 200，含 checkpointer 模式（实测 redis）
- [x] `GET /metrics` 输出 prometheus 文本指标（自定义 8 项指标均有定义）
- [x] 实施期间 v2 只读未改：v2 源码 mtime ≤ 2026-10-09 15:08，会话内零改动（仅 __pycache__ 编译产物刷新）
- [x] 图中无意图分类/快速通道节点（编译图 nodes 仅 __start__/agent/tools/__end__），请求前置 LLM 分类调用为 0

## P1 核心链路
- [x] curl SSE 依次收到 meta（served_by=agent）→ tool{phase:start/end} → llm_chunk → complete{usage 含 input_tokens/output_tokens/total_ms/shortcut_hit}（商品问答实测 4771/403/12145ms）
- [x] 商品问题触发 `product_card` 事件（items 4 商品，来自 search_products JSON 解析）
- [x] 政策类问题触发 `citation` 事件（refs 含 no/question），回答含 [1][2][3] 引用；search_faq 返回值含 score（RRF 分）且未在工具内卡阈值
- [x] search_faq 检索为三路召回（BM25 question + knn + BM25 similar_questions）+ RRF(k=60) 融合（es_client.search_faq_v3 代码可查证，冒烟 top3 命中售后类）
- [x] `submit_aftersale` 触发 `interrupt` 事件（action=submit_aftersale/payload 七字段/resume_token=session_id），interrupt 后 aftersale_order 计数=0 未写库
- [x] resume approved=true → 售后单 RMA202610100038468775A2 创建成功，ai_action_audit result=success（id=8）
- [x] approved=false → 不写库，审计 result=rejected（id=7）
- [x] 同一中断重复 resume → 409 ALREADY_PROCESSED（Redis SETNX 幂等），未重复执行
- [x] 上游异常时工具返回可读错误文本（timed_call 统一转换，Task 2 冒烟未登录路径验证），流不中断，prometheus 计入工具错误

## 安全门
- [x] 无 X-User-Id 头且无 user_id 参数 → 401
- [x] 同一用户 1 分钟内第 21 次请求 → 429（函数级 21 次第 21 次 429；HTTP 层 21 并发 17×429；rate_limited_total{scope=user} 0→1.0）
- [x] 注入样本 → 降级应答、不调 LLM/工具、日志含 injection_blocked+request_id
- [x] 超 2000 字符输入被截断（2718 字符实测正常应答，无 413/400）

## 记忆与知识库
- [x] 请求组装前 get_preferences 注入 SystemMessage（chat.py:198/206，prefs 为空跳过、异常降级）；Task 4 实测 LLM 提取偏好并覆盖写 hash
- [x] 整理游标存 Redis（memcur:{u}:{s}=4 实测），无进程内游标变量；memlock NX EX 60 防并发
- [x] `python -m scripts.build_faq_index` 两次执行幂等（mall_faq_v3 _count=19 不变，top3 与 RRF 分一致），alias mall_faq 指向 mall_faq_v3
- [x] `ai_chat_feedback` 建表后 POST /api/v3/feedback 落库成功（request_id/rating/comment/shortcut_hit 字段完整）

## 契约与依赖
- [x] SSE 事件字段与 spec §6 表逐字段一致（meta/llm_chunk/tool/product_card/citation/interrupt/complete/error 全部实测或代码核对）
- [x] requirements.txt 仅追加 langfuse==2.60.5/prometheus_client==0.23.1/structlog==25.5.0，.venv 安装成功
- [x] 所有内部 Java 调用带 X-Internal-Secret、超时 3s、仅连接错误重试 1 次（app/core/http_client.py request_internal）

## v2 旧代码删除（Task 7，Task 6 全部通过后执行）
- [x] `ai-service/main.py`、`graph/`、`agents/`、`core/`、`config/`、`api/` 已删除
- [x] `scripts/` 下 v2 专属脚本（import_faq.py/eval_intent.py/golden_set.py）已删除；`static/` 旧 demo 页已删除；杂散旧 `venv/` 已删除；另清理 tests/test_streaming.py、docs/streaming*.md，README 重写为 v3 实况
- [x] 保留项完好：`scripts/faq_seed.py`、`scripts/build_faq_index.py`、`scripts/sql/`、`requirements.txt`、`.venv/`、`.env`、`app/`、`tests/`（空）、`Dockerfile`、`.env.example`、`.gitignore`
- [x] 全项目 grep 无 `from config.`/`from graph.`/`from agents.`/`from core.`/`from api.` 残留 import（0 命中）
- [x] 删除后 v3 独立启动冒烟通过：`python -m app.main` → health 200（graph=ready）→ 一次完整 SSE 对话（meta→llm_chunk×34→complete）
- [x] 项目记忆中 ai-service 启动命令已更新为 `.venv\Scripts\python.exe -m app.main`
