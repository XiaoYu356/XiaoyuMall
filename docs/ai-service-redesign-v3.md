# AI 智能客服 v3 重设计方案（从 0 到可落地、可观测）

> 版本：v3.0 草案 | 日期：2026-10-09
> 定位：废弃现有 `agents/`（老链路）+ `graph/`（v2 三路由链路）双轨结构，从 0 重建单一链路的智能客服服务。
> 目标形态：可演示、可上线、可观测、可评估。

---

## 1. 现状的病根（为什么重来）

| # | 病根 | 后果 |
|---|------|------|
| 1 | 双链路并存（`agents/` 老链路 + `graph/` 新链路） | 改一处要顾两处，认知负担大，接口行为不一致 |
| 2 | 意图分类节点作为所有请求的前置 | 每个请求多一次 LLM 调用（+300~800ms），有 6s 超时风险，误判即全链路错向 |
| 3 | 三条代码路径（faq_fast / query_fast / agent） | 条件边回退逻辑分散，测试组合爆炸 |
| 4 | 完全黑盒 | 无 token 用量、无延迟分位数、无错误率、无回答质量数据；出问题靠猜 |
| 5 | 无评估体系 | 改 prompt 全凭感觉，改完不知道变好还是变坏 |
| 6 | SSE 端点裸奔 | 无限流、无独立鉴权、SSE 生命周期有已知问题 |
| 7 | 记忆整理游标在进程内 | 多实例不可用，重启丢游标 |

**保留的资产（已验证，直接迁移）**：Redis Checkpointer（含降级 MemorySaver）、LangGraph `interrupt()` HITL 硬确认、`/resume` 幂等恢复、审计表 `ai_action_audit`、ES 混合检索客户端、embedding 封装、Java 侧工具 API 与 `X-Internal-Secret` 内部鉴权。

---

## 2. 设计原则

1. **单一链路**：一个服务、一条主干流程、一个 Agent。所有"快"都通过确定性手段（缓存、阈值短路）实现，而不是靠 LLM 分类器分流。
2. **可观测是一等公民**：trace / metrics / logs / evals 四件套在 P2 阶段就要能用，不是"以后补"。
3. **评估驱动**：prompt 与工具的每次变更都要过 golden 数据集回归，用数据代替感觉。
4. **工具即契约**：每个工具有类型化参数、超时、重试、明确的错误语义；LLM 拿到的错误信息是"可读的、可行动的"。
5. **写操作硬保障**：HITL `interrupt()` + 审计落库不因重构而退化。

---

## 3. 总体架构

```
                        ┌─────────────────────────────────────────────┐
                        │              ai-service (FastAPI)           │
                        │                                             │
 用户/小程序 ──SSE──────▶│  ①安全门            ②单 Agent（唯一主干）    │
                        │  鉴权/限流/防护 ──▶  ReAct ⇄ Tools           │
                        │                     （search_faq 为其一，    │ ⇄ HITL interrupt
                        │                      模型自主决定是否检索）   │
                        │                                             │
                        │  ③横切观测：Langfuse trace │ /metrics │ JSON日志 │
                        └─────────────────────────────────────────────┘
                              │                    │                │
                              ▼                    ▼                ▼
                        Redis(checkpoint/     Java 微服务        MySQL(审计/反馈)
                        限流/偏好记忆)        (商品/订单/券/售后)
```

### 3.1 核心决策 A：砍掉意图分类，改为「RAG 当工具（agentic RAG）+ 单 Agent」

> 修订：检索前置短路不再是默认设计。对照业界高质量实现（LangGraph 官方 agentic RAG 模板、LlamaIndex QueryEngineTool、Dify Agent+知识库）后确认：**检索注册为工具、由模型决定何时调用**是标准模式，链路更简单且无阈值调参负担。阈值短路降级为可选优化（见 3.1.1）。

| 维度 | v2（三路由） | v3 |
|------|-------------|-----|
| 请求前置 LLM 开销 | 1 次分类调用 | **0 次** |
| 代码路径 | 3 条 + 条件边回退 | **1 条** |
| 错误形态 | 路由错误（整条路走错） | 工具选择错误（有完整上下文可自我纠正） |
| FAQ 延迟 | 分类 + 检索 + 生成 | 1~2 次 LLM 轮次（决定调工具 → 带上下文作答） |

**search_faq 工具（agentic RAG）**：检索与其他业务工具同级注册，模型自主决定"是否查知识库"。拿到结果后自检相关性——不相关就换问法重查或如实说不知道（CRAG 思路），回答带 [1] 引用。工具描述写清边界："平台政策/规则/费用/流程类问题调用本工具；查商品、订单、优惠券等实时数据不要用本工具"。

#### 3.1.1 可选优化：FAQ 阈值短路（默认关闭）

当 metrics 显示 FAQ 类请求占比 >40% 且 TTFT 不达标时，再启用"embedding → 检索 → top1 相似度 ≥ 0.92 → 0 LLM 直答"前置旁路。它在入口加一层旁路，不改动 Agent 主干——启用与否是增量，不是重构。

**单 Agent 工具集**（search_faq 为其一）：

```
商品域：search_products / get_product_detail
优惠域：get_available_coupons / calculate_coupon_discount / get_my_coupons*
订单域：get_my_orders / get_order_detail / get_logistics_timeline
售后域：submit_aftersale* / complete_return_refund*   (* = HITL 写操作)
知识域：search_faq
```

### 3.2 核心决策 B：可观测四件套

| 件 | 选型 | 说明 |
|----|------|------|
| Traces | **Langfuse v2 自托管**（1 容器 + PostgreSQL） | 每次请求一条 trace；span 级覆盖短路检索、每次 LLM 调用（含 token/成本/prompt 版本）、每次工具调用；前端 `meta` 事件带 `trace_url`，点击可回放 |
| Metrics | `prometheus-client` 暴露 `/metrics` | TTFT、端到端延迟分位数（按 短路/Agent 分开统计）、工具错误率、短路命中率、转人工率、token 成本 |
| Logs | `structlog` JSON 日志 + request_id 贯穿 | `request_id = trace_id`，日志与 trace 可互相跳转 |
| Evals | Langfuse Datasets + LLM-as-judge 脚本 | golden 数据集 50 条起步；改 prompt/工具前后跑回归，输出对比报告 |

> 为什么选 Langfuse v2：v3 自托管需要 clickhouse + minio + redis + postgres 四件套，对当前规模过重；v2 单容器 + postgres 即可，接口与 v3 兼容，后续可平滑升级。若不想自托管，可退而用 LangSmith（云，有免费额度），代码只换一个 callback 配置。

### 3.3 核心决策 C：安全层前置

- **鉴权**：复用网关传递的用户身份（header 用户 ID + `X-Internal-Secret` 服务间校验），ai-service 不自己发 token。
- **限流**：Redis 滑动窗口，per-user 20 次/分钟 + 全局兜底 200 QPS；SSE 端点单独限额（连接数 per-user ≤ 3）。
- **输入防护**：长度截断（2000 字符）、prompt 注入规则检测（命中则降级为"无法回答该问题"并记录 trace 标签）、敏感词过滤。
- **HITL + 审计**：完整保留 v2 的 `interrupt()` 硬中断、`/resume` 幂等、`ai_action_audit` 落库。

---

## 4. 服务内部结构

```
ai-service/
├── app/
│   ├── main.py                  # FastAPI 入口；lifespan 统一管理连接池
│   ├── core/
│   │   ├── config.py            # pydantic-settings；所有环境变量集中于此
│   │   ├── observability.py     # Langfuse callback、/metrics、structlog 初始化
│   │   ├── security.py          # 鉴权依赖、Redis 限流器、注入检测
│   │   └── http_client.py       # 内部服务调用封装：超时(3s)/重试(1次)/错误契约
│   ├── graph/
│   │   ├── builder.py           # 编译图：agent 单节点 + checkpointer
│   │   ├── state.py             # GraphState：messages/cards/citations/usage…
│   │   ├── checkpointer.py      # 迁移自 v2（Redis 优先，降级 MemorySaver）
│   │   └── nodes/
│   │       └── agent.py         # create_react_agent + 系统提示词
│   ├── tools/                   # 每工具一文件；pydantic 参数 + 错误契约 + 耗时埋点
│   │   ├── product_tools.py
│   │   ├── coupon_tools.py
│   │   ├── order_tools.py
│   │   ├── aftersale_tools.py   # 内含 interrupt 硬中断（迁移自 v2）
│   │   └── faq_tools.py         # search_faq 工具（agentic RAG：平台政策知识检索）
│   ├── pipeline/
│   │   └── faq_shortcut.py      # （可选，默认不启用）阈值短路：embedding→检索→直答
│   ├── memory/
│   │   ├── profile.py           # 用户偏好（Redis hash，读写）
│   │   └── consolidator.py      # 记忆整理（游标存 Redis，多实例安全）
│   ├── api/
│   │   ├── chat.py              # GET /api/v3/chat/stream（SSE）
│   │   ├── resume.py            # POST /api/v3/resume（幂等）
│   │   ├── feedback.py          # POST /api/v3/feedback（👍/👎）
│   │   └── health.py
│   └── evals/
│       ├── datasets/golden_v1.jsonl   # 50 条：问题→期望行为/答案要点
│       └── run_eval.py                # 本地/CI 回归脚本（LLM-as-judge）
├── tests/                       # 工具单测（mock Java API）+ 短路阈值测试
├── Dockerfile
└── docker-compose.yml           # ai-service + langfuse + langfuse-db
```

**关键差异**：`agents/` 整个删除；`graph/nodes/intent_classifier.py`、`faq_fast.py`、`query_fast.py` 不再存在，其能力分别由 `pipeline/faq_shortcut.py`（检索+直答）与 `tools/faq_tools.py`、agent 内工具选择承接。

---

## 5. 一次请求的生命周期

```
1. 网关带用户身份转发 → SSE /api/v3/chat/stream?session_id=xxx&q=...
2. 安全门：鉴权 → 限流检查 → 注入检测 → 生成 request_id，创建 Langfuse trace
3. 组装上下文：checkpoint(thread_id=u{user}:s{session}) + 用户偏好注入 system prompt
4. Agent 循环：LLM 规划 → 并行工具调用（每个工具 span 记录耗时/结果/错误）→ … → 生成回答；
   search_faq 与其他工具同级，模型自主决定是否查知识库（agentic RAG）
   └─ 写操作工具内部：只读预检 → interrupt(payload) → SSE interrupt 事件 → 挂起
5. 后处理（异步）：审计（写操作）、记忆整理（每 4 条消息，游标存 Redis）、偏好更新
6. SSE complete 事件：携带 usage（prompt/completion tokens、总耗时）
7. 用户点 👍/👎 → POST /feedback → chat_feedback 表（关联 request_id）→ 抽样进 golden 数据集
```

**HITL 恢复**：`POST /api/v3/resume`（幂等键 = thread_id + interrupt 序号），`Command(resume=True/False)` 恢复，与 v2 语义一致。

---

## 6. SSE 事件契约 v3（版本化，前端按此实现）

| 事件 type | data | 说明 |
|-----------|------|------|
| `meta` | `{request_id, trace_url, served_by: "shortcut"\|"agent"}` | 首事件；trace_url 可直接打开 Langfuse |
| `llm_chunk` | `{text}` | 流式 token（短路直答时切块模拟） |
| `tool` | `{name, phase: start\|end, ok, elapsed_ms?}` | 工具生命周期 |
| `product_card` | `{items: [{id,name,price,image,sales}]}` | 商品卡片 |
| `citation` | `{refs: [{no, question}]}` | FAQ 引用编号对照 |
| `interrupt` | `{action, payload, resume_token}` | HITL 确认卡片 |
| `complete` | `{usage: {input_tokens, output_tokens, total_ms, shortcut_hit}}` | 收尾统计 |
| `error` | `{code, message, recoverable}` | 统一错误；recoverable=true 时前端提示重试 |

**兼容性**：`product_card`/`citation` 为新增；`complete.usage` 为新增字段（前端旧版忽略未知字段即可）；事件名与 v2 不冲突，mall-web 前端仅需增量适配。

---

## 7. 指标定义与目标

| 指标 | 定义 | 目标 | 采集 |
|------|------|------|------|
| TTFT p50/p95 | 首个 llm_chunk 距请求开始 | < 1.2s / < 2.5s | Prometheus histogram |
| 端到端延迟 p95（Agent 路径） | 请求→complete | < 10s | 同上 |
| 短路延迟 p95 | 请求→complete（shortcut 命中） | < 500ms | 同上 |
| FAQ 短路命中率 | 命中数 / 总请求 | 30%~50%（低于 20% 检查阈值） | 计数器 |
| 短路误答率 | 命中但用户 👎 或转人工 | < 3% | 反馈表关联 |
| 工具调用错误率 | 工具 error / 总调用 | < 2% | span 统计 |
| 转人工率 | 转人工 / 总会话 | 基线后持续下降 | 计数器 |
| Token 成本 | 每会话 input+output tokens | 趋势监控（无硬目标） | Langfuse |

---

## 8. 评估闭环（evals）

1. **golden 数据集** `golden_v1.jsonl`，每条：`{id, question, expected_intent_path, expected_tools[], answer_points[], user_context}`。覆盖：FAQ 命中/未命中、商品查询、券计算、订单查询、售后确认/取消、注入样本、闲聊边界。首批 50 条，来源：真实会话抽样 + 手工构造。
2. **回归脚本** `run_eval.py`：跑数据集 → 收集（走了哪条路、调了哪些工具、最终答案）→ 三项评分：
   - 路由正确率（shortcut/agent 判定是否符合 expected_intent_path）
   - 工具选择正确率（expected_tools 召回）
   - 回答质量（LLM-as-judge 按 answer_points 打 1-5 分）
3. **流程约束**：改动 prompt、工具描述、阈值 → 必须先跑 `run_eval.py`，三项不劣化才能合入。报告存 Langfuse Experiment，可对比任意两次。

---

## 9. 数据模型增量

```sql
-- 新增：用户反馈（评估闭环的数据源）
CREATE TABLE ai_chat_feedback (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  request_id VARCHAR(64) NOT NULL,        -- = trace_id，可跳 Langfuse
  user_id BIGINT NOT NULL,
  session_id VARCHAR(64) NOT NULL,
  rating TINYINT NOT NULL,                -- 1=赞 0=贬
  comment VARCHAR(500),
  shortcut_hit TINYINT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  KEY idx_user (user_id), KEY idx_request (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 保留：ai_action_audit（结构不变）
```

---

## 10. 分阶段落地路线图

| 阶段 | 内容 | 验收标准 |
|------|------|----------|
| **P0 骨架与契约**（0.5周） | 目录、config、SSE v3 schema 冻结、内部 API 契约冻结、docker-compose 骨架 | 服务空图可启动；curl 连 SSE 能收到 meta+complete 心跳 |
| **P1 核心链路**（1周） | 单 Agent + 5 域工具迁移（pydantic 化，search_faq 即 agentic RAG）+ checkpointer + HITL/resume | v2 功能对齐清单逐项手测通过；写操作仍需确认卡片 |
| **P2 可观测**（1周） | Langfuse 全埋点、/metrics、JSON 日志、meta.trace_url | 任一回复可点击回放 trace（含每次工具耗时与 token）；Grafana 可见 §7 指标 |
| **P3 安全与反馈**（0.5周） | 限流、注入检测、/feedback + chat_feedback 表 | 压测下限流生效（429）；👍👎 落库且关联 request_id |
| **P4 评估闭环**（1周） | golden_v1 50 条、run_eval.py、judge 评分 | 改一条 prompt 能自动产出前后对比报告 |
| **P5 压测与加固**（0.5周） | locust 压测、SSE 生命周期修复（重连/去重监听）、优雅停机；（可选）若 metrics 触发则启用 FAQ 阈值短路 | 50 并发持续 10min：错误率 <1%，p95 达标 |

每个阶段独立可演示（P1 结束即可替换线上 v2 流量入口）。

---

## 11. 风险与对策

| 风险 | 对策 |
|------|------|
| 短路阈值 0.92 过高/过低 | 阈值进 config；评估集里放边界样本；上线初期 `served_by` 打点观察一周再调 |
| 单 Agent 工具多导致选择错误 | 工具描述精写（一句话职责 + 一句话不要用的情况）；工具 ≤ 12 个，超了再做域内分组合并 |
| Langfuse 自托管维护成本 | v2 单容器 + 托管 postgres 复用现有 MySQL 运维习惯；仅内网暴露 |
| FAQ 直答出错（知识库过期） | 短路答案同样走 👎 反馈；👎 率异常自动告警到 trace 标签 |
| 迁移期间新旧行为不一致 | P1 验收用"对齐清单"逐条过；v2 代码冻结只修 bug，新功能一律进 v3 |

---

## 12. 与 v2 的能力对照（自查清单）

- [x] 会话持久化（checkpoint）→ 保留迁移
- [x] HITL 写操作确认 → 保留迁移
- [x] 审计落库 → 保留迁移
- [x] FAQ 引用回答 → search_faq 工具（agentic RAG，业界标准模式）；阈值短路为可选优化（默认关闭）
- [x] 商品查询 → agent 工具（更强：模型可组合调用）
- [x] 用户偏好记忆 → 保留，游标改 Redis（修复多实例缺陷）
- [x] SSE 流式 → 契约 v3（新增 meta/usage/citation）
- [ ] 意图分类节点 → **删除**（由模型工具选择替代）
- [ ] query_fast/faq_fast 节点 → **删除**（并入 agent 工具集）
- [ ] agents/ 老链路 → **删除**
- [NEW] 全链路 trace/metrics/logs
- [NEW] golden 数据集 + 回归评估
- [NEW] 限流 / 注入防护 / 反馈闭环

---

## 13. FAQ 知识库建设（RAG 落地细节）

### 13.1 核心认知：客服 KB 靠"条目化"，不靠"文档切分"

通用文档 RAG（合同、手册）才需要 chunk 切分与 overlap。客服知识天然是**一问一答的原子条目**，正确做法是把政策文档**拆成结构化条目**，每条自成一个可独立回答的单元：

```json
{
  "id": "faq_return_001",
  "question": "7天无理由退货的条件是什么",
  "similar_questions": ["什么情况可以7天退货", "无理由退货有要求吗"],
  "answer": "商品签收后7天内，不影响二次销售（吊牌完整、未洗涤）可申请无理由退货。定制类、生鲜、贴身衣物除外。",
  "category": "售后政策",
  "tags": ["退货", "7天无理由"],
  "version": 3,
  "updated_at": "2026-10-09"
}
```

**切分规则**（政策 markdown → 条目）：

| 规则 | 说明 |
|------|------|
| 按问答边界切 | 一条政策含多种情形就拆多条（退货-7天无理由 / 退货-质量问题 / 退货-运费承担），每条独立成答 |
| 长条目再拆 | 单条 answer > 500 字按小标题/句子边界拆，拆后每条补写独立 question |
| 碎条目合并 | answer < 30 字的相邻条目合并 |
| 同义问法生成 | 每条用 LLM 批量生成 2~5 条 similar_questions（口语化、含错别字变体）——**客服 RAG 召回率的最大杠杆** |
| 人工抽检 | LLM 生成的问法抽检 10%，不合格的条目整条打回 |

### 13.2 ES 索引设计

```json
{
  "settings": {
    "analysis": { "analyzer": { "ik_smart_a": { "type": "custom", "tokenizer": "ik_smart" } } }
  },
  "mappings": {
    "properties": {
      "question":          { "type": "text",   "analyzer": "ik_max_word", "search_analyzer": "ik_smart" },
      "similar_questions": { "type": "text",   "analyzer": "ik_max_word", "search_analyzer": "ik_smart" },
      "answer":            { "type": "text",   "enabled": false },
      "question_vector":   { "type": "dense_vector", "dims": 1024, "index": true,
                             "similarity": "cosine", "index_options": { "type": "hnsw", "m": 16, "ef_construction": 128 } },
      "category":          { "type": "keyword" },
      "tags":              { "type": "keyword" },
      "version":           { "type": "integer" }
    }
  }
}
```

要点：
- **BM25 打在 question + similar_questions 上**，answer 不参与召回（`enabled:false` 只存不索引）——answer 的书面措辞和用户口语差异大，参与召回只会带噪音
- **向量字段只存 question 的 embedding**（多条 similar_questions 各自向量化、多向量字段任一命中即召回），检索时用"用户问题向量"匹配"预设问题向量"——问法对问法，比对答案匹配准得多
- answer 以 `_source` 返回给工具，供模型引用作答
- 索引名带版本 `mall_faq_v3`，更新知识库时重建新索引 + alias 切换，支持回滚

### 13.3 检索策略（search_faq 工具内部）

```
入参 query（agent 传入提炼后的问题）
  → embedding(query)                        # qwen text-embedding, 1024 维
  → 三路并行召回 top10：
      ① BM25(question, query)               # 关键词精确（型号、金额、天数）
      ② knn(question_vector, query_vector)  # 语义相似（口语改写）
      ③ BM25(similar_questions, query)      # 同义问法匹配
  → RRF 融合排序 → top3
  → 返回 [{question, answer, score, category}]
```

- **score 透传给模型**：工具返回值里带相似分，由模型自检相关性（CRAG）——分低就换问法重查或如实说不知道，不在工具里硬卡阈值
- 中文分词：索引用 `ik_max_word`（细粒度召回），搜索用 `ik_smart`（粗粒度防过切）
- **rerank 二期再说**：条目数 < 500 时三路 RRF 足够；知识库上千条且错召回明显时，加 qwen-rerank 对 top10 重排
- 工具描述写明："传入用户问题的提炼版（保留关键数字与商品词），一次查不到可换关键词重查，最多 2 次"

### 13.4 知识库运营闭环

1. **未命中回流**：search_faq 返回空/低分时 trace 打标 `faq_miss`，每周导出高频未命中问题 → 新条目（这是知识库自然生长的来源）
2. **答案修正**：👍👎 反馈 + `request_id` 可回放 trace 定位到当时命中的条目 → 直接改条目
3. **上线前最小集**：P1 手工整理 30~50 条核心条目 JSON（退货/运费/支付/优惠券/发货五类），脚本 `scripts/build_faq_index.py` 灌入 ES
4. **评估**：golden 集的 FAQ 用例单独统计召回率（expected 条目是否出现在 top3）

### 13.5 明确不做的

- 不引入向量数据库（Milvus/Qdrant）——ES 8 的 knn + 现有运维栈够用
- 不做通用文档解析器（PDF/Word）——知识源头直接维护为条目 JSON/markdown 表格
- 不做自动从订单/商品库生成知识——客服知识是人工资产，自动生成必错

