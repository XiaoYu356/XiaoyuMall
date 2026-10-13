"""共享 HTTP 客户端与内部服务调用封装。

- 模块级单例 httpx.AsyncClient（lifespan 创建/关闭），全服务复用连接池
- request_internal()：自动携带 X-Internal-Secret；仅对 httpx.TransportError
  （连接未建立等传输层错误）重试 1 次；重试仍失败抛 UpstreamError
- 非 2xx 不抛异常：由调用方按状态码处理（返回 response）
"""
import httpx

from app.core.config import settings

_client: httpx.AsyncClient | None = None


async def init_http_client() -> None:
    """应用启动时调用一次：创建共享 AsyncClient（lifespan）。"""
    global _client
    _client = httpx.AsyncClient(timeout=httpx.Timeout(3.0))


async def close_http_client() -> None:
    """应用关闭时调用：释放连接池。"""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_http_client() -> httpx.AsyncClient:
    """获取共享客户端；未初始化（或已关闭）时直接暴露编程错误。"""
    if _client is None:
        raise RuntimeError("HTTP client 未初始化，请先调用 init_http_client()")
    return _client


class UpstreamError(RuntimeError):
    """上游服务不可达（传输层重试后仍失败）。"""


def _internal_headers() -> dict:
    """内部服务间调用凭证：Java 侧拦截器据此放行（归属校验仍按 userId 执行）。"""
    if not settings.INTERNAL_SECRET:
        return {}
    return {"X-Internal-Secret": settings.INTERNAL_SECRET}


async def request_internal(
    method: str,
    url: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
    timeout: float = 3.0,
) -> httpx.Response:
    """调用 Java 内部服务：自动带 X-Internal-Secret，传输层错误重试 1 次。

    非 2xx 不抛异常（返回 response，由调用方按状态码处理）。
    """
    client = get_http_client()
    headers = _internal_headers()
    try:
        return await client.request(
            method, url, params=params, json=json, timeout=timeout, headers=headers
        )
    except httpx.TransportError:
        # 仅传输层错误（连接未建立/超时等）重试一次
        try:
            return await client.request(
                method, url, params=params, json=json, timeout=timeout, headers=headers
            )
        except httpx.TransportError as e:
            raise UpstreamError(f"上游服务不可达: {url} ({e})") from e
