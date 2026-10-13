"""健康检查与 Prometheus 指标端点。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.config import settings
from app.graph.checkpointer import checkpointer_mode

router = APIRouter()


@router.get("/api/v3/health")
async def health(request: Request) -> dict:
    """健康检查：含 checkpointer 模式与图装配状态。"""
    graph_state = (
        "ready"
        if getattr(request.app.state, "ai_graph", None) is not None
        else "not_assembled"
    )
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "checkpointer": checkpointer_mode(),
        "graph": graph_state,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus 指标导出。"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
