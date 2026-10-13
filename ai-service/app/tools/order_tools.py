"""订单域工具：订单列表 / 订单详情 / 物流轨迹（经 order-service 内部接口）。

迁移自 v2 graph/tools/user_tools.py 的 get_my_orders / get_order_detail
与 graph/tools/aftersale_tools.py 的 get_logistics_timeline。
user_id 经 RunnableConfig 注入（LLM 不提供身份）；返回人类可读文本。
"""
import logging
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.core.config import settings
from app.core.http_client import request_internal
from app.tools.base import ToolError, _current_user_id, timed_call

logger = logging.getLogger(__name__)

_ORDER_STATUS = {0: "待付款", 1: "待发货", 2: "待收货", 3: "已完成", 4: "已取消"}


@tool
async def get_my_orders(
    config: RunnableConfig,
    status: Optional[int] = None,
    limit: int = 5,
) -> str:
    """查询当前登录用户的订单列表。用户问"我的订单""我买了什么""订单进度"时使用。
    无需向用户索要用户ID，系统已知当前登录用户。

    Args:
        status: 按订单状态筛选，可选。0待付款 1待发货 2待收货 3已完成 4已取消
        limit: 返回条数，默认5
    """

    async def _run() -> str:
        user_id = _current_user_id(config)
        if not user_id:
            return "当前未登录，无法查询订单。请先登录后再试。"

        params: dict = {"userId": user_id, "pageNum": 1, "pageSize": limit}
        if status is not None:
            params["status"] = status
        resp = await request_internal(
            "GET", f"{settings.ORDER_SERVICE_URL}/api/v1/orders", params=params
        )
        if resp.status_code != 200:
            raise ToolError(f"查询订单失败: HTTP {resp.status_code}")
        data = resp.json().get("data") or {}
        records = data.get("records") or []
        if not records:
            return "您还没有订单记录。"
        lines = [
            f"订单号:{o.get('orderNo')} | "
            f"状态:{_ORDER_STATUS.get(o.get('status'), '未知')} | "
            f"实付:¥{o.get('payAmount')} | 下单时间:{o.get('createTime')}"
            for o in records
        ]
        total = data.get("total")
        header = (
            f"共 {total} 笔订单，最近 {len(records)} 笔："
            if total is not None else f"最近 {len(records)} 笔订单："
        )
        return header + "\n" + "\n".join(lines)

    return await timed_call("get_my_orders", _run, service="订单服务")


@tool
async def get_order_detail(
    config: RunnableConfig,
    order_no: str,
) -> str:
    """按订单号查询订单详情（含商品明细、收货信息、金额）。用户提供了订单号时使用。

    Args:
        order_no: 订单号
    """

    async def _run() -> str:
        user_id = _current_user_id(config)
        if not user_id:
            return "当前未登录，无法查询订单。请先登录后再试。"

        resp = await request_internal(
            "GET", f"{settings.ORDER_SERVICE_URL}/api/v1/orders/no/{order_no}",
            params={"userId": user_id},
        )
        if resp.status_code != 200:
            raise ToolError(f"查询订单失败: HTTP {resp.status_code}")
        order = resp.json().get("data")
        if not order:
            return f"未找到订单号 {order_no} 的订单。"

        # 越权双保险：后端已按 userId 校验归属，这里再核一次
        if str(order.get("userId")) != user_id:
            logger.info("拦截越权订单查询 user=%s orderNo=%s", user_id, order_no)
            return f"未找到订单号 {order_no} 的订单。"

        items = order.get("items") or []
        item_lines = "\n".join(
            f"  - {item.get('productName')} × {item.get('quantity')}"
            f"（单价¥{item.get('price')}）"
            for item in items
        )
        text = (
            f"订单号:{order.get('orderNo')}\n"
            f"状态:{_ORDER_STATUS.get(order.get('status'), '未知')}\n"
            f"商品总额:¥{order.get('totalAmount')} | 优惠:¥{order.get('discountAmount')} "
            f"| 实付:¥{order.get('payAmount')}\n"
            f"收货人:{order.get('receiverName')} {order.get('receiverPhone')}\n"
            f"收货地址:{order.get('receiverAddress')}\n"
            f"下单时间:{order.get('createTime')}"
        )
        if item_lines:
            text += f"\n商品明细:\n{item_lines}"
        return text

    return await timed_call("get_order_detail", _run, service="订单服务")


@tool
async def get_logistics_timeline(
    config: RunnableConfig,
    order_no: str,
) -> str:
    """查询订单物流轨迹。用户问"货到哪了""物流进度""发货了吗""催发货"时使用。

    Args:
        order_no: 订单号
    """

    async def _run() -> str:
        user_id = _current_user_id(config)
        if not user_id:
            return "当前未登录，无法查询物流。请先登录后再试。"

        resp = await request_internal(
            "GET", f"{settings.ORDER_SERVICE_URL}/api/v1/orders/no/{order_no}/logistics",
            params={"userId": user_id},
        )
        if resp.status_code != 200:
            raise ToolError(f"查询物流失败: HTTP {resp.status_code}")
        nodes = resp.json().get("data") or []
        if not nodes:
            return "该订单暂无物流信息（可能尚未发货或已取消）。"
        lines = [
            f"{node.get('time')} 【{node.get('status')}】{node.get('description')}"
            for node in nodes
        ]
        return "物流轨迹（最新在下方）：\n" + "\n".join(lines)

    return await timed_call("get_logistics_timeline", _run, service="订单服务")
