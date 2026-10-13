# XiaoyuMall - 智能百货平台

基于 Spring Cloud Alibaba 的智能百货平台微服务架构，集成商品、优惠券、订单、售后等核心电商能力，并落地了一个基于 LangGraph ReAct Agent 的 AI 购物助手（v3），通过 SSE 流式交互提供智能客服、知识库问答、商品查询、优惠券领取、订单管理等一站式 AI 体验。

## 🏗️ 技术架构

### Java 微服务技术栈

| 技术 | 版本 | 说明 |
|-----|------|------|
| Spring Boot | 3.2.2 | 应用开发框架 |
| Spring Cloud | 2023.0.0 | 微服务框架 |
| Spring Cloud Alibaba | 2023.0.0-RC1 | 微服务组件 |
| Sa-Token | 1.37.0 | 权限认证框架 |
| Nacos | 2.3.0 | 服务注册与配置中心 |
| MySQL | 8.0 | 关系型数据库 |
| Redis | 8.0 | 分布式缓存（含 RediSearch/RedisJSON 内核模块） |
| MyBatis-Plus | 3.5.5 | ORM 框架 |
| MinIO | RELEASE.2023-03 | 对象存储 |
| RocketMQ | 5.1.0 | 消息队列 |
| Elasticsearch | 8.11.3 | 商品检索 + FAQ 知识库（IK 中文分词） |
| Prometheus | v2.54.0 | 指标采集 |
| Grafana | 10.4.2 | 监控看板（provisioning 自动加载 AI 服务看板） |

### AI 服务技术栈

| 技术 | 说明 |
|-----|------|
| Python 3.11 + FastAPI | AI 服务主体 |
| LangGraph | 单 Agent（`create_react_agent`）+ `AsyncRedisSaver` Checkpointer（降级 MemorySaver） |
| 本地 bge-m3 | 向量化（自动适配 CUDA FP16 / CPU FP32） |
| 本地 bge-reranker-v2-m3 | Cross-Encoder 精排（评测集校准阈值分级） |
| Elasticsearch | FAQ 三路召回（BM25 question / kNN / BM25 similar_questions）→ RRF 融合 |
| structlog + Langfuse v4 + Prometheus | JSON 日志 / 全链路 Trace / 业务指标 |

### 前端技术栈

| 技术 | 版本 | 说明 |
|-----|------|------|
| Vue | 3.4.0 | 渐进式 JavaScript 框架 |
| Vue Router | 4.2.5 | 官方路由管理器 |
| Pinia | 2.1.7 | 新一代状态管理工具 |
| Element Plus | 2.5.0 | Vue 3 组件库（管理后台） |
| Axios | 1.6.5 | HTTP 客户端 |
| Vite | 5.0.10 | 下一代前端构建工具 |

### 项目结构

```
XiaoyuMall/
├── backend/                        # Java 微服务
│   ├── mall-common/               # 公共模块（Result / 异常 / Redis 常量）
│   ├── mall-gateway/              # 网关服务（Sa-Token AuthFilter + CORS）
│   ├── user-service/              # 用户服务（注册登录 / 地址）
│   ├── product-service/           # 商品服务（CRUD / ES 搜索 / AI 代理转发）
│   ├── coupon-service/            # 优惠券服务（四版本并发策略：V0→V1→V2→V3）
│   ├── order-service/             # 订单服务（购物车 / 订单 / 售后）
│   ├── es-plugins/                # ES IK 分词器
│   ├── grafana/                   # Grafana provisioning（AI 服务 8 面板看板）
│   ├── prometheus/                 # Prometheus 抓取配置
│   ├── rocketmq/                   # RocketMQ broker 配置
│   ├── sql/                       # 数据库初始化脚本 + 种子数据 + 压测脚本
│   ├── docker-compose.yaml         # 基础设施编排（Nacos/MySQL/Redis/ES/RocketMQ/MinIO/Prometheus/Grafana）
│   └── pom.xml                    # Maven 父项目
├── ai-service/                     # AI 购物助手服务（v3，Python FastAPI）
│   ├── app/
│   │   ├── main.py                # FastAPI 入口（lifespan 预热模型）
│   │   ├── core/                  # config / observability / security / es_client / embeddings / reranker / audit
│   │   ├── graph/                 # state / checkpointer / builder / nodes/agent
│   │   ├── tools/                 # 五域 11 工具（product/coupon/order/aftersale/faq；aftersale 含 HITL interrupt）
│   │   ├── memory/                # 双层记忆：短期 Redis Checkpointer + 长期偏好蒸馏
│   │   └── api/                   # chat(SSE v3) / resume(幂等) / feedback / health / metrics
│   ├── scripts/
│   │   ├── build_faq_index.py     # FAQ 索引构建（alias 原子切换）
│   │   ├── faq_seed.py            # FAQ 种子数据生成
│   │   └── eval/                  # 检索评测 + 重排阈值校准
│   ├── README.md
│   └── requirements.txt
├── frontend/
│   ├── mall-admin/                # 管理后台（商品 / 订单 / 优惠券 / 用户 / 知识库 / 缺口管理）
│   └── mall-web/                  # C 端商城（首页 / 商品 / 购物车 / 结算 / AI 助手）
├── docs/
│   └── ai-service-redesign-v3.md  # AI 服务 v3 重构设计文档
└── README.md
```

## 🚀 快速开始

### 环境要求

- **Java 后端**：JDK 17+、Maven 3.6+
- **AI 服务**：Python 3.11+、（可选）NVIDIA CUDA GPU 用于本地 bge 模型加速
- **前端**：Node.js 18+、npm 9+
- **基础设施**：Docker 20+（运行 MySQL / Redis / Nacos / ES / RocketMQ / MinIO / Prometheus / Grafana）

### 1. 启动基础设施

```bash
cd backend
docker-compose up -d
```

启动后检查各组件：
| 组件 | 访问地址 |
|-----|---------|
| Nacos | http://localhost:8848/nacos（nacos / nacos） |
| MySQL | `localhost:3306`（root / root） |
| Redis | `localhost:6379` |
| Elasticsearch | http://localhost:9201 |
| Kibana | http://localhost:8601 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3003（admin / admin） |
| MinIO Console | http://localhost:9001（admin / admin123456） |

> 注：ai-service 的 docker-compose 条目默认注释，本地开发直接用 Python 启动。

### 2. 初始化数据库

```bash
# PowerShell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -uroot -proot --default-character-set=utf8mb4 -e "source backend/sql/init.sql"
```

或手动在 MySQL 客户端执行 `backend/sql/init.sql`。

### 3. 启动 Java 微服务

```bash
cd backend
mvn clean install -DskipTests

# 按顺序启动（每个新开终端）
cd mall-gateway && mvn spring-boot:run         # :8080
cd user-service && mvn spring-boot:run          # :8081
cd product-service && mvn spring-boot:run       # :8082
cd coupon-service && mvn spring-boot:run        # :8083
cd order-service && mvn spring-boot:run         # :8084
```

### 4. 启动 AI 服务

```powershell
cd ai-service

# 首次：创建虚拟环境并安装依赖
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt

# 配置环境变量
Copy-Item .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY 和服务地址

# 启动（lifespan 自动预热 bge-m3 + bge-reranker 模型）
.venv\Scripts\python.exe -m app.main
# 默认 8000 端口
```

启动后：
- 健康检查：`GET http://localhost:8000/api/v3/health`
- Prometheus 指标：`GET http://localhost:8000/metrics`
- 重建 FAQ 索引：`.venv\Scripts\python.exe -m scripts.build_faq_index`

### 5. 启动前端

**管理后台**（mall-admin）：
```bash
cd frontend/mall-admin
npm install
npm run dev         # http://localhost:3000  默认 admin / 123456
```

**C 端商城**（mall-web）：
```bash
cd frontend/mall-web
npm install
npm run dev         # Vite 默认端口（通常 5173）
```

## 📦 服务端口总览

| 服务 | 端口 | 说明 |
|-----|------|------|
| mall-gateway | 8080 | API 网关（Sa-Token 鉴权 + 路由） |
| user-service | 8081 | 用户 / 注册 / 登录 / 地址 |
| product-service | 8082 | 商品 / 分类 / 搜索 / AI 代理转发 |
| coupon-service | 8083 | 优惠券模板 / 领取 / 核销（四版本并发策略） |
| order-service | 8084 | 购物车 / 订单 / 售后 |
| ai-service | 8000 | AI 购物助手（Python FastAPI，SSE 流式） |
| Nacos | 8848 | 服务注册与配置中心 |
| MySQL | 3306 | 关系型数据库 |
| Redis | 6379 | 分布式缓存 + LangGraph Checkpointer |
| Elasticsearch | 9201 | 商品索引 + FAQ 知识库 |
| Kibana | 8601 | ES 可视化 |
| RocketMQ NameServer | 9876 | 消息队列命名服务 |
| RocketMQ Broker | 10911 | 消息队列 Broker |
| MinIO | 9000 / 9001 | 对象存储 + Console |
| Prometheus | 9090 | 指标采集 |
| Grafana | 3003 | 监控看板（provisioning 自动加载 AI 服务面板） |

## 🎯 功能特性

### Java 微服务

- ✅ 用户注册 / 登录（Sa-Token JWT）
- ✅ 商品管理 / 分类 / ES 搜索
- ✅ 库存管理（Redis 预扣 + DB 最终扣减）
- ✅ 优惠券领取四版本并发策略（V0 超卖 → V1 原子扣减 → V2 Redis Lua 预扣 → V3 RocketMQ 削峰）
- ✅ 订单创建 / 超时取消 / 购物车
- ✅ 售后申请 / 处理
- ✅ MinIO 文件上传
- ✅ RocketMQ 异步削峰（优惠券 / 订单）
- ✅ Elasticsearch 商品搜索 + IK 中文分词

### AI 购物助手（v3）

- ✅ **ReAct Agent 自主决策**：单 Agent 挂载五域 11 工具，模型自主路由
- ✅ **Agentic RAG**：三路召回（BM25 + kNN + 相似问法）→ RRF 融合 → Cross-Encoder 精排 → 置信度分级（本地 bge-reranker）
- ✅ **HITL 写操作保护**：LangGraph `interrupt()` 硬确认 + `ai_action_audit` 审计落库（aftersale 退款等）
- ✅ **SSE 流式交互**：agent_start → intent → tool_start → llm_chunk → complete 全链路事件流
- ✅ **双层记忆**：短期 LangGraph AsyncRedisSaver 支撑 HITL interrupt/resume，长期 Letta 式异步偏好蒸馏（TTL 30 天）
- ✅ **上下文压缩**：pre_model_hook 非破坏性裁剪（仅 llm_input_messages，checkpoint 状态保留），tiktoken cl100k_base 精确计数，20k token 预算
- ✅ **三级可观测**：Langfuse v4 Trace + Prometheus Histogram 指标（TTFT / E2E / Tool 耗时）+ structlog JSON 日志
- ✅ **知识库数据飞轮**：FAQ CRUD + MySQL `faq_gap` 缺口信号采集 + ES alias 原子切换重建 + 检索评测闭环

### 已完成性能优化

| 优化项 | 前后对比 |
|--------|---------|
| Logback AsyncAppender | 高并发 QPS 从 ~450 提升至无明显瓶颈 |
| PyTorch CPU → CUDA + FP16 | search_faq 总耗时 11.5s → 1.5s（7.2x 加速），rerank 阶段 7.6s → 0.46s（16.6x） |
| LangGraph pre_model_hook 上下文压缩 | CPU 版 PyTorch + approximate 计数下 4x 低估真实 token，现已用 tiktoken cl100k_base 精确计数 |
| es_client async→sync + to_thread | 解决 Windows + Docker 端口转发环境下 anyio httpx.AsyncClient ReadError |

## 📖 AI 服务架构简述

AI 服务设计文档：[ai-service-redesign-v3.md](docs/ai-service-redesign-v3.md)

```
用户 → mall-web → product-service(代理 /api/v1/ai/**) → ai-service :8000
                                                              │
                                                              ▼
                                              create_react_agent (LangGraph)
                                                    │  │  │  │  │
                                              product coupon order aftersale faq_tools
                                                │       │      │        │
                                                ▼       ▼      ▼        ▼
                                          user-service coupon  order    ES FAQ
                                          product      service service  (BM25+kNN+similar)
                                                                           │
                                                                           ▼
                                                                    RRF 融合 → 本地 bge-reranker
                                                                           │
                                                                           ▼
                                                                    阈值分级 (T_HIGH / T_MID / T_LOW)
```

- AI 服务不注册 Nacos，product-service 通过固定地址 `http://localhost:8000` 直连代理
- 内部服务调用统一携带 `X-Internal-Secret` 头
- 本地开发时 bge 模型自动检测 CUDA → FP16 加速，无 GPU 回退 CPU FP32

## 🔧 配置说明

### Nacos（各 Java 微服务 application.yaml）

```yaml
spring:
  cloud:
    nacos:
      discovery:
        server-addr: localhost:8848
      config:
        server-addr: localhost:8848
        file-extension: yaml
```

### AI 服务（ai-service/.env）

```bash
OPENAI_API_KEY=your-dashscope-api-key
OPENAI_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus-2025-07-28
PRODUCT_SERVICE_URL=http://localhost:8082
INTERNAL_SECRET=xiaoyu-internal-2026
```

### Grafana

Provisioning 配置在 `backend/grafana/provisioning/`，启动后 Grafana 自动加载 AI 服务 8 面板看板，无需手动配置。访问 http://localhost:3003 查看。

## 📝 开发指南

- 遵循阿里巴巴 Java 开发规范 + Lombok
- AI 服务启动命令统一使用 `.venv\Scripts\python.exe -m app.main`（Windows）或 `.venv/bin/python -m app.main`（Linux），不要直接 `python main.py`
- AI 评测脚本必须 `cd ai-service && .venv\Scripts\python.exe -m scripts.eval.run_retrieval_eval`，且 `CONCURRENCY=1`（本地 bge CUDA 推理线程不安全）
- Redis 关键数据使用命名 volume `backend_redis-data`，禁止 anonymous volume

## 📄 许可证

Apache License 2.0
