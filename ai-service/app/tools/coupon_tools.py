"""优惠域工具：领券中心、我的优惠券、优惠计算（经 coupon-service 内部接口）。

迁移自 v2 两处实现：agents/tools/coupon_tools.py（领券中心/优惠计算）
+ graph/tools/user_tools.py（我的优惠券）。get_my_coupons 的 user_id
经 RunnableConfig 注入（LLM 不提供身份）。全部返回人类可读文本。
"""
import logging
from datetime import datetime

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.core.config import settings
from app.core.http_client import request_internal
from app.tools.base import ToolError, _current_user_id, timed_call

logger = logging.getLogger(__name__)

_COUPON_TYPE = {1: "满减券", 2: "折扣券", 3: "现金券"}


@tool
async def get_available_coupons(config: RunnableConfig) -> str:
    """获取领券中心当前可领取的优惠券列表，只返回用户未领取过、有库存且未过期的优惠券；
    用户已领取过的券不会出现在可领列表，会单独提示。
    用户问"有什么优惠券可以领""领券中心有什么活动"时使用。"""

    async def _run() -> str:
        # 已领取集合：同一模板一人仅能领一张（user_coupon 唯一索引 uk_user_template），
        # 先查用户已领的全部券，用于从可领列表中剔除并单独提示
        claimed_ids = set()
        claimed_names = {}
        user_id = _current_user_id(config)
        if user_id:
            my_resp = await request_internal(
                "GET", f"{settings.COUPON_SERVICE_URL}/api/v1/coupons/user/{user_id}",
                params={"pageSize": 100},
            )
            if my_resp.status_code == 200:
                for uc in (my_resp.json().get("data") or {}).get("records") or []:
                    tid = uc.get("templateId")
                    if tid is not None:
                        claimed_ids.add(tid)
                        claimed_names[tid] = uc.get("templateName", "N/A")

        resp = await request_internal(
            "GET", f"{settings.COUPON_SERVICE_URL}/api/v1/coupons/available",
            params={"pageSize": 20},
        )
        if resp.status_code != 200:
            raise ToolError(f"获取可领优惠券失败: HTTP {resp.status_code}")
        records = (resp.json().get("data") or {}).get("records") or []
        if not records:
            return "当前暂无可领取的优惠券。"

        now = datetime.now()
        available = []
        claimed_visible = []
        for c in records:
            # 领券中心过滤：剩余库存 <= 0 或已过期的券不展示
            remaining = c.get("totalCount", 0) - c.get("usedCount", 0)
            end_time_str = c.get("endTime", "")
            expired = False
            if end_time_str:
                try:
                    expired = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S") < now
                except ValueError:
                    pass
            if remaining <= 0 or expired:
                continue
            # 用户已领取过的券：不可重复领取，从可领列表剔除、单独提示
            if c.get("id") in claimed_ids:
                claimed_visible.append(
                    f"{claimed_names.get(c.get('id'), c.get('templateName', 'N/A'))}"
                    f"（面值 ¥{c.get('couponValue', 'N/A')}）"
                )
                continue
            available.append(
                f"模板ID:{c.get('id')} | 名称:{c.get('templateName', 'N/A')} | "
                f"类型:{_COUPON_TYPE.get(c.get('couponType'), '未知')} | "
                f"面值:{c.get('couponValue', 'N/A')} | 最低消费:¥{c.get('minAmount', 0)} | "
                f"剩余:{remaining}张 | 有效期至:{end_time_str}"
            )

        parts = []
        if available:
            parts.append("\n".join(available))
        else:
            parts.append("当前没有你可领取的新优惠券。")
        if claimed_visible:
            parts.append(
                f"另外，以下 {len(claimed_visible)} 张优惠券你已领取过，可在【我的优惠券】中查看使用：\n"
                + "\n".join(claimed_visible)
            )
        return "\n\n".join(parts)

    return await timed_call("get_available_coupons", _run, service="优惠券服务")


@tool
async def get_my_coupons(config: RunnableConfig, only_usable: bool = True) -> str:
    """查询当前登录用户已领取的优惠券。用户问"我有什么优惠券""我的券"时使用。
    无需向用户索要用户ID，系统已知当前登录用户。

    Args:
        only_usable: 是否只返回可用（未使用、未过期）的券，默认 True
    """

    async def _run() -> str:
        user_id = _current_user_id(config)
        if not user_id:
            return "当前未登录，无法查询优惠券。请先登录后再试。"
        params = {"status": 0} if only_usable else {}
        resp = await request_internal(
            "GET", f"{settings.COUPON_SERVICE_URL}/api/v1/coupons/user/{user_id}",
            params=params,
        )
        if resp.status_code != 200:
            raise ToolError(f"查询优惠券失败: HTTP {resp.status_code}")
        records = (resp.json().get("data") or {}).get("records") or []
        if not records:
            return "您当前没有可用的优惠券。"
        lines = [
            f"优惠券ID:{c.get('id')} | 名称:{c.get('templateName', 'N/A')} | "
            f"类型:{_COUPON_TYPE.get(c.get('couponType'), '未知')} | "
            f"面值:{c.get('couponValue', 'N/A')} | 最低消费:¥{c.get('minAmount', 0)}"
            for c in records
        ]
        return f"您有 {len(records)} 张可用优惠券：\n" + "\n".join(lines)

    return await timed_call("get_my_coupons", _run, service="优惠券服务")


@tool
async def calculate_coupon_discount(coupon_id: int, order_amount: float) -> str:
    """计算使用指定优惠券后的优惠金额和最终实付价格。

    Args:
        coupon_id: 优惠券ID
        order_amount: 订单金额（元）
    """

    async def _run() -> str:
        resp = await request_internal(
            "POST", f"{settings.COUPON_SERVICE_URL}/api/v1/coupons/calculate",
            params={"couponId": coupon_id, "orderAmount": order_amount},
        )
        if resp.status_code != 200:
            raise ToolError(f"计算优惠失败: HTTP {resp.status_code}")
        # 后端返回 Result<BigDecimal>，data 为优惠金额数字（券不可用时为 0）
        discount = float(resp.json().get("data") or 0)
        final_amount = round(order_amount - discount, 2)
        return (
            f"优惠券ID:{coupon_id}\n"
            f"订单金额:¥{order_amount}\n"
            f"优惠金额:¥{discount}\n"
            f"实付金额:¥{final_amount}"
        )

    return await timed_call("calculate_coupon_discount", _run, service="优惠券服务")
