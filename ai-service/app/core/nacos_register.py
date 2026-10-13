"""Nacos 服务注册：用 httpx 调 Nacos Open API 完成实例注册、心跳保活与注销。

ai-service 不走 Spring Cloud Nacos Discovery（Java 生态），此处以最小依赖
（仅 httpx）实现临时实例注册 + 定时心跳 + 优雅注销，使 Gateway 能通过
lb://ai-service 路由到本服务。
"""
import asyncio
import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_heartbeat_task: asyncio.Task | None = None
_http_client: httpx.Client | None = None


def _base_url() -> str:
    return f"http://{settings.NACOS_HOST}:{settings.NACOS_PORT}"


def _register_sync() -> None:
    """同步注册临时实例到 Nacos（ephemeral=true，需客户端发心跳保活）。"""
    params = {
        "serviceName": settings.SERVICE_NAME,
        "ip": settings.SERVICE_IP,
        "port": settings.PORT,
        "groupName": settings.NACOS_GROUP,
        "namespaceId": settings.NACOS_NAMESPACE,
        "ephemeral": "true",
    }
    resp = _http_client.post(
        f"{_base_url()}/nacos/v1/ns/instance", params=params, timeout=5.0
    )
    resp.raise_for_status()
    if resp.text.strip() != "ok":
        logger.warning("Nacos 注册返回非 ok: %s", resp.text)


def _heartbeat_sync() -> None:
    """发送实例心跳（PUT /nacos/v1/ns/instance/beat）。"""
    beat = json.dumps({
        "ip": settings.SERVICE_IP,
        "port": settings.PORT,
        "serviceName": settings.SERVICE_NAME,
        "cluster": "DEFAULT",
        "beatPort": 0,
        "period": settings.NACOS_HEARTBEAT_INTERVAL * 1000,
    })
    params = {
        "serviceName": settings.SERVICE_NAME,
        "beat": beat,
        "namespaceId": settings.NACOS_NAMESPACE,
        "groupName": settings.NACOS_GROUP,
    }
    resp = _http_client.put(
        f"{_base_url()}/nacos/v1/ns/instance/beat", params=params, timeout=5.0
    )
    resp.raise_for_status()


def _deregister_sync() -> None:
    """从 Nacos 注销实例。"""
    params = {
        "serviceName": settings.SERVICE_NAME,
        "ip": settings.SERVICE_IP,
        "port": settings.PORT,
        "groupName": settings.NACOS_GROUP,
        "namespaceId": settings.NACOS_NAMESPACE,
    }
    resp = _http_client.delete(
        f"{_base_url()}/nacos/v1/ns/instance", params=params, timeout=5.0
    )
    resp.raise_for_status()


async def _heartbeat_loop() -> None:
    """定时心跳守护协程（每 NACOS_HEARTBEAT_INTERVAL 秒发一次）。"""
    interval = settings.NACOS_HEARTBEAT_INTERVAL
    while True:
        try:
            await asyncio.to_thread(_heartbeat_sync)
        except Exception as e:
            logger.warning("Nacos 心跳失败(忽略，下次重试): %s", e)
        await asyncio.sleep(interval)


async def register_to_nacos() -> None:
    """注册到 Nacos 并启动心跳守护协程。注册失败不阻断启动。"""
    global _http_client, _heartbeat_task
    _http_client = httpx.Client()
    try:
        await asyncio.to_thread(_register_sync)
        logger.info(
            "Nacos 注册成功 service=%s ip=%s port=%s",
            settings.SERVICE_NAME, settings.SERVICE_IP, settings.PORT,
        )
    except Exception as e:
        logger.warning("Nacos 注册失败(不阻断启动，Gateway 暂时路由不到): %s", e)
        _http_client.close()
        _http_client = None
        return
    _heartbeat_task = asyncio.create_task(_heartbeat_loop(), name="nacos-heartbeat")


async def deregister_from_nacos() -> None:
    """注销 Nacos 实例并停止心跳（lifespan 收尾用）。"""
    global _http_client, _heartbeat_task
    if _heartbeat_task is not None:
        _heartbeat_task.cancel()
        try:
            await _heartbeat_task
        except asyncio.CancelledError:
            pass
        _heartbeat_task = None
    if _http_client is not None:
        try:
            await asyncio.to_thread(_deregister_sync)
            logger.info("Nacos 注销完成 service=%s", settings.SERVICE_NAME)
        except Exception as e:
            logger.warning("Nacos 注销失败(忽略): %s", e)
        _http_client.close()
        _http_client = None
