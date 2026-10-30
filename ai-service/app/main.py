"""v3 服务入口：lifespan 装配横切层，图装配失败不阻断启动（后续任务补齐）。

启动方式（cwd=ai-service）：.venv\\Scripts\\python.exe -m app.main
"""
import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.http_client import close_http_client, init_http_client
from app.core.nacos_register import deregister_from_nacos, register_to_nacos
from app.core.observability import setup_logging
from app.graph.checkpointer import init_checkpointer
from app.memory import close_redis

logger = logging.getLogger(__name__)


def _warmup_local_models() -> None:
    """后台预加载本地模型（bge-m3 / bge-reranker-v2-m3）。

    两模型均为首次调用时懒加载（各 10~40 秒），不预热则重启服务后的
    第一个知识库问题要背上模型加载耗时。守护线程执行，失败不阻断启动
    （首次调用时会再尝试加载）。
    """
    try:
        from app.core.embeddings import _load_local_encoder
        from app.core.reranker import _load_local_reranker

        _load_local_encoder()
        _load_local_reranker()
        logger.info("本地模型预热完成 bge-m3 + bge-reranker-v2-m3")
    except Exception as e:
        logger.warning("本地模型预热失败(忽略，首次调用时再加载): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_http_client()

    # 本地模型预热：守护线程后台加载，不阻塞服务启动（load 有线程锁，
    # 与首个请求的懒加载天然互斥）
    threading.Thread(target=_warmup_local_models, daemon=True, name="model-warmup").start()

    try:
        # checkpointer：Redis 优先，失败自动降级 memory（不阻断启动）
        checkpointer = await init_checkpointer()
        # 供"清空会话"端点联动删除 thread checkpoint
        app.state.checkpointer = checkpointer

        # 图装配属后续任务（app/graph/builder.py 未就绪时降级为 not_assembled）
        try:
            from app.graph.builder import build_graph

            app.state.ai_graph = build_graph(checkpointer)
        except Exception as e:
            app.state.ai_graph = None
            logging.getLogger(__name__).warning(
                "图装配失败（后续任务），graph=not_assembled，不阻断启动: %s", e
            )

        # Nacos 注册：注册到 Nacos + 启动心跳守护协程，使 Gateway lb://ai-service 可路由
        await register_to_nacos()

        yield
    finally:
        await deregister_from_nacos()
        await close_http_client()
        await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.chat import router as chat_router  # noqa: E402
from app.api.feedback import router as feedback_router  # noqa: E402
from app.api.health import router as health_router  # noqa: E402
from app.api.knowledge import router as knowledge_router  # noqa: E402
from app.api.memory import router as memory_router  # noqa: E402
from app.api.resume import router as resume_router  # noqa: E402

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(resume_router)
app.include_router(feedback_router)
app.include_router(knowledge_router)
# memory 端点挂 /api/v1/ai 前缀（与前端 ai.js 请求路径对齐）
app.include_router(memory_router, prefix="/api/v1/ai")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=False)
