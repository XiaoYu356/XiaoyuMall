"""v2 前端代理兼容端点：/api/v1/ai/memory/**（挂载时带该前缀，路径与响应结构
逐字段对齐 v2 api/routes.py 与 product-service AIController 代理转发，前端无感迁移）。

Java 代理（AIController.java）实际转发并依赖的最小集合：
- GET  /memory/conversation/{user_id}?session_id=&limit=  会话历史回显
- POST /resume（见 app/api/resume.py，Java 在 body 传 user_id）
另保留 v2 已有的偏好读写端点（GET/POST /memory/preferences），响应结构同 v2。
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.memory.history import clear_session, get_history
from app.memory.profile import get_preferences, set_preference

router = APIRouter()


class PreferenceRequest(BaseModel):
    user_id: str
    key: str
    value: str


@router.get("/memory/conversation/{user_id}")
async def get_conversation_history(
    user_id: str,
    session_id: Optional[str] = None,
    limit: int = 20,
):
    """会话历史（Java 代理 GET /api/v1/ai/memory/conversation/{userId} 透传）。"""
    try:
        if session_id:
            history = await get_history(user_id, session_id, limit)
        else:
            history = []
        return JSONResponse(content={
            "success": True,
            "message": f"获取到{len(history)}条对话记录",
            "data": {"history": history},
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/preferences/{user_id}")
async def get_user_preferences(user_id: str):
    """读全部用户偏好（响应结构与 v2 一致）。"""
    try:
        preferences = await get_preferences(user_id)
        return JSONResponse(content={
            "success": True,
            "message": "获取用户偏好成功",
            "data": {"preferences": preferences},
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/preferences")
async def set_user_preference(body: PreferenceRequest):
    """写单个偏好字段（字段名/响应结构与 v2 PreferenceRequest 一致）。"""
    try:
        await set_preference(body.user_id, body.key, body.value)
        return JSONResponse(content={
            "success": True,
            "message": f"已保存偏好: {body.key}",
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/session/{user_id}/{session_id}")
async def clear_conversation_session(user_id: str, session_id: str):
    """清除指定会话（Java 代理 DELETE /api/v1/ai/memory/session/{userId}/{sessionId} 透传）。"""
    try:
        await clear_session(user_id, session_id)
        return JSONResponse(content={
            "success": True,
            "message": "会话已清除",
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
