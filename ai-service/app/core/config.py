"""v3 全局配置：变量名与 v2 config/settings.py 完全一致（保证 .env 兼容），
新增 v3 专属字段（全部带默认值，.env 缺失也能启动）。
"""
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Smart Mall AI Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    OPENAI_MODEL: str = "qwen3.8-max"
    # 快速模型：意图分类等轻量结构化任务（免费额度仅 qwen3.8-max 可用）
    OPENAI_MODEL_FAST: str = "qwen3.8-max"

    PRODUCT_SERVICE_URL: str = "http://localhost:8082"
    COUPON_SERVICE_URL: str = "http://localhost:8083"
    USER_SERVICE_URL: str = "http://localhost:8081"
    ORDER_SERVICE_URL: str = "http://localhost:8084"

    # 内部服务间共享密钥：直连 Java 服务时经 X-Internal-Secret 头携带，
    # 与 order-service application.yaml 的 internal.secret 保持一致
    INTERNAL_SECRET: str = "xiaoyu-internal-2026"

    # Elasticsearch（mall_product 索引由 Java 侧维护，mall_faq 由本服务维护）
    ES_URL: str = "http://localhost:9201"

    # MySQL：AI 写操作审计表（ai_action_audit）落库，与后端 docker-compose 一致
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root"
    MYSQL_DB: str = "mall_order"

    MEMORY_MAX_TURNS: int = 10

    # ---- v3.1 检索重排分级（本地 bge-reranker-v2-m3，替代 CRAG LLM 判级） ----
    # 端点 {RERANK_API_BASE}/services/rerank/text-rerank/text-rerank；
    # key 缺省复用 OPENAI_API_KEY（同一百炼账号）
    RERANK_API_BASE: str = "https://dashscope.aliyuncs.com/api/v1"
    RERANK_API_KEY: Optional[str] = None
    RERANK_MODEL: str = "qwen3.7-text-rerank"
    RERANK_TIMEOUT: float = 5.0
    # RRF 融合去重后的候选池大小（送重排；重排需要裁剪空间，直接 top3 无精排价值）
    # GPU 环境下 rerank 很快（8 候选 ≈ 0.5s），8 比 10 省 ~20% 重排开销且评测 hit@3 不退化
    RERANK_CANDIDATES: int = 8
    # 置信度三档阈值：由 scripts/eval/calibrate_rerank_thresholds.py 在评测集上按
    # 正/负样本分数分布校准（2026-10-11，n=355 正 / 30 负）：
    # 正样本(gold最佳分) P5=0.88，负样本(域外最高分) max=0.53，分离带 [0.53,0.88]；
    # 阈值取分离带内稳健整数点（bge-reranker-v2-m3 raw logits 刻度，校准报告
    # calibration_report_20261012_113824.json：正样本 p5=0.48，负样本 max=-3.36，
    # 分离带 [-3.36, 0.48]；域外误进 0、正样本存活 ≥95% 双向留漂移缓冲）：
    # >=0 高置信引用；[-3.0,0) 中置信引用并标注；<-3.0 剔除
    # （T_LOW=-7.3 为负样本 P50 观测线，在线动作与 T_MID 合并，供校准观测与级联演进）
    RERANK_T_HIGH: float = 0.0
    RERANK_T_MID: float = -3.0
    RERANK_T_LOW: float = -7.3

    # ---- v3 新增：可观测（全部带默认值，未配置即禁用） ----
    # Langfuse trace（v2 SDK：public/secret key 任一为空则不启用）
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = ""

    # ---- v3 新增：安全与限流（令牌桶算法） ----
    # per-user 每分钟补充令牌数（稳态速率，20/min ≈ 0.33 个/秒）
    RATE_LIMIT_USER_PER_MIN: int = 20
    # per-user 桶容量（允许的瞬时突发请求数；首次请求或长时间空闲后满桶）
    RATE_LIMIT_USER_BURST: int = 20
    # 全局每秒补充令牌数（稳态速率，QPS）
    RATE_LIMIT_GLOBAL_QPS: int = 200
    # 全局桶容量（允许的瞬时突发请求数）
    RATE_LIMIT_GLOBAL_BURST: int = 200
    # 单用户并发 SSE 连接上限
    SSE_MAX_CONN_PER_USER: int = 3
    # 用户输入最大字符数（超出截断）
    INPUT_MAX_CHARS: int = 2000

    # 日志级别（structlog JSON 输出）
    LOG_LEVEL: str = "INFO"

    # 服务自身对外基础地址（拼 Langfuse trace_url 用）
    SERVICE_BASE_URL: str = ""

    # ---- Nacos 注册（ai-service 直连注册，Gateway 经 lb://ai-service 路由） ----
    NACOS_HOST: str = "localhost"
    NACOS_PORT: int = 8848
    NACOS_NAMESPACE: str = "public"
    NACOS_GROUP: str = "DEFAULT_GROUP"
    SERVICE_NAME: str = "ai-service"
    # 注册到 Nacos 的 IP（留空则自动探测本机 IP）
    SERVICE_IP: str = "127.0.0.1"
    # 心跳间隔秒（Nacos 默认 5s 心跳，≤15s 标记健康）
    NACOS_HEARTBEAT_INTERVAL: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
