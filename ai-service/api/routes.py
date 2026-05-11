from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from api.schemas import (
    AnalysisRequest,
    QuickAnalysisRequest,
    CouponRequest,
    AnalysisResponse,
    FullAnalysisResponse,
    HealthResponse
)
from core.coordinator import AgentCoordinator
from core.workflow import ShoppingAssistantWorkflow
from core.streaming import StreamingCoordinator
from config.settings import settings
from datetime import datetime

router = APIRouter()

coordinator = AgentCoordinator()
workflow = ShoppingAssistantWorkflow(coordinator)
streaming_coordinator = StreamingCoordinator(coordinator)


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.now().isoformat()
    )


@router.post("/analyze", response_model=FullAnalysisResponse)
async def full_analysis(request: AnalysisRequest):
    try:
        result = await coordinator.analyze_and_recommend(
            product_id=request.product_id,
            user_id=request.user_id,
            user_query=request.user_query
        )
        
        return FullAnalysisResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/product", response_model=AnalysisResponse)
async def product_analysis(request: QuickAnalysisRequest):
    try:
        result = await coordinator.quick_analysis(request.product_id)
        
        return AnalysisResponse(
            success=True,
            message="商品分析完成",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/price", response_model=AnalysisResponse)
async def price_analysis(request: QuickAnalysisRequest):
    try:
        result = await coordinator.price_check(request.product_id)
        
        return AnalysisResponse(
            success=True,
            message="价格分析完成",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/coupon", response_model=AnalysisResponse)
async def coupon_analysis(request: CouponRequest):
    try:
        result = await coordinator.find_best_coupon(
            user_id=request.user_id,
            order_amount=request.order_amount
        )
        
        return AnalysisResponse(
            success=True,
            message="优惠券分析完成",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflow/analyze", response_model=AnalysisResponse)
async def workflow_analysis(request: AnalysisRequest):
    try:
        result = await workflow.run(
            product_id=request.product_id,
            user_id=request.user_id,
            user_query=request.user_query
        )
        
        return AnalysisResponse(
            success=True,
            message="工作流分析完成",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=AnalysisResponse)
async def get_history(limit: int = 10):
    try:
        history = coordinator.get_execution_history(limit)
        
        return AnalysisResponse(
            success=True,
            message=f"获取最近{len(history)}条执行记录",
            data={"history": history}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream/analyze")
async def stream_analysis(request: AnalysisRequest):
    return StreamingResponse(
        streaming_coordinator.stream_analysis(
            product_id=request.product_id,
            user_id=request.user_id,
            user_query=request.user_query
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/stream/chat")
async def stream_chat(request: AnalysisRequest):
    return StreamingResponse(
        streaming_coordinator.stream_llm_response(
            product_id=request.product_id,
            user_query=request.user_query
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
