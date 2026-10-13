# 智能百货平台 - AI 购物助手服务（v3）

## 项目简介

单 Agent（ReAct）+ agentic RAG 的智能购物助手：一个 Agent 挂载五域 11 个工具（商品/优惠/订单/售后/知识），由模型自主决定是否检索知识库（search_faq，CRAG 式自检），无意图分类前置。设计文档见 `docs/ai-service-redesign-v3.md`（仓库根目录）。

## 技术栈

- **Python 3.11** + **FastAPI**
- **LangGraph** - 单 Agent（create_react_agent）+ Redis Checkpointer（AsyncRedisSaver，降级 MemorySaver）
- **Elasticsearch** - FAQ 三路召回（BM25 question + knn + BM25 similar_questions）→ RRF 融合
- **Langfuse v2**（可选，trace）/ **prometheus-client**（/metrics）/ **structlog**（JSON 日志）

## 项目结构

```
ai-service/
├── app/                    # v3 唯一代码位置
│   ├── main.py             # FastAPI 入口（lifespan：checkpointer→graph→http client）
│   ├── core/               # config / observability / security / http_client / audit / es_client / embeddings
│   ├── graph/              # state / checkpointer / builder / nodes/agent（单 Agent 图）
│   ├── tools/              # 五域 11 工具（product/coupon/order/aftersale/faq；aftersale 含 HITL interrupt）
│   ├── memory/             # profile（偏好）/ history（会话）/ consolidator（游标存 Redis）
│   └── api/                # chat（SSE v3）/ resume（幂等）/ feedback / health / memory 兼容
├── scripts/
│   ├── faq_seed.py         # FAQ 种子数据
│   ├── build_faq_index.py  # FAQ v3 知识库构建（幂等重建 + alias 切换）
│   └── sql/v3_feedback.sql # ai_chat_feedback 建表
└── requirements.txt
```

## 启动

```powershell
cd d:\code\XiaoyuMall\ai-service
.venv\Scripts\python.exe -m app.main   # 默认 8000 端口；$env:PORT 可覆盖
```

前置：Redis 8+（含 RediSearch 模块）、ES 9201（mall_faq_v3 索引已建）、Java 微服务 8081-8084、`.env` 配置 LLM key。

## 主要接口

| 接口 | 说明 |
|------|------|
| `GET /api/v3/chat/stream?q=&session_id=` | SSE v3：meta / tool / product_card / citation / llm_chunk / interrupt / complete / error |
| `POST /api/v3/resume` | HITL 确认恢复（Redis SETNX 幂等，重复提交 409） |
| `POST /api/v3/feedback` | 用户反馈 → ai_chat_feedback |
| `GET /api/v3/health`、`GET /metrics` | 健康检查（含 checkpointer 模式）/ Prometheus 指标 |
| `/api/v1/ai/memory/**` | v2 前端代理兼容端点（会话历史/偏好） |

## FAQ 知识库重建

```powershell
.venv\Scripts\python.exe -m scripts.build_faq_index   # 幂等可重复执行
```

## 安全

- 身份：`X-User-Id` 头优先，回退 `user_id` query 参数
- 限流：per-user 20 次/分钟 + 全局 200 QPS；SSE 连接 per-user ≤ 3
- 输入：2000 字符截断 + prompt 注入规则检测（命中降级应答）
- 写操作：LangGraph `interrupt()` 硬确认 + `ai_action_audit` 审计落库
- 内部调用：`X-Internal-Secret` 头 + 超时 3s
