"""售后域工具：退款/退货申请与退货退款完成（HITL 写操作，经 order-service 内部接口）。

设计要点（人在回路 Human-in-the-loop，LangGraph interrupt 硬中断，自 v2 全量迁移）：
- submit_aftersale / complete_return_refund 是写操作：工具内部先只读校验并组装
  确认卡片数据，然后 interrupt(payload) 挂起整个图；SSE 层把 payload 推给前端
  渲染确认卡片，用户点击后 POST /resume 以 Command(resume=True/False) 恢复
- interrupt 恢复时本工具会从头重跑，因此 interrupt 之前只做幂等的只读查询，
  任何写库动作必须放在 interrupt 之后
- 用户批准/拒绝/执行失败均落审计表 ai_action_audit（best-effort，不阻断流程）
- 与其他工具一致：user_id / session_id 经 RunnableConfig 注入，LLM 无需也不能提供
- interrupt payload 字段（action/order_no/items/type/type_text/refund_amount/reason）
  与 v2 前端确认卡片契约一致，不得改动
"""
import logging
from typing import Literal, Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.types import interrupt

from app.core.audit import write_audit
from app.core.config import settings
from app.core.http_client import request_internal
from app.tools.base import ToolError, _current_session_id, _current_user_id, timed_call

logger = logging.getLogger(__name__)

_AFTERSALE_STATUS = {
    0: "待审核", 1: "审核通过(待寄回)", 2: "退货中",
    3: "仓库已签收", 4: "退款中", 5: "已完成", 6: "已驳回",
}
_AFTERSALE_TYPE = {1: "仅退款", 2: "退货退款"}


async def _fetch_order(order_no: str, user_id: str) -> Optional[dict]:
    """按订单号取订单（内部接口，按归属校验）。"""
    resp = await request_internal(
        "GET", f"{settings.ORDER_SERVICE_URL}/api/v1/orders/no/{order_no}",
        params={"userId": user_id},
    )
    if resp.status_code != 200:
        return None
    return resp.json().get("data")


def _item_names(order: dict) -> str:
    items = order.get("items") or []
    return "、".join(
        f"{item.get('productName')}×{item.get('quantity')}" for item in items
    ) or "(未知商品)"


@tool
async def submit_aftersale(
    config: RunnableConfig,
    order_no: str,
    type: Literal[1, 2],
    reason: str,
) -> str:
    """提交退款/退货售后申请（写操作）。用户明确表达退款/退货意愿时直接调用；
    系统会自动暂停并向用户展示确认卡片，用户点击确认后才真正执行，无需你再次征求确认。

    Args:
        order_no: 要申请售后的订单号
        type: 售后类型，1=仅退款（未发货等），2=退货退款（需寄回商品）
        reason: 售后原因（根据用户描述概括）
    """

    async def _run() -> str:
        user_id = _current_user_id(config)
        if not user_id:
            return "当前未登录，无法申请售后。请先登录后再试。"

        # --- 只读校验 + 组装确认卡片（interrupt 恢复后工具从头重跑，此处保持幂等） ---
        try:
            order = await _fetch_order(order_no, user_id)
        except Exception as e:
            logger.warning("售后查询订单失败 order_no=%s: %s", order_no, e)
            raise ToolError(f"查询订单信息时出错: {e}")

        # 越权双保险：后端已按 userId 校验归属，这里再核一次
        if not order or str(order.get("userId")) != user_id:
            return f"未找到订单号 {order_no} 的订单。"
        if order.get("status") not in (1, 2, 3):
            return "当前订单状态不支持申请售后（仅已支付/已发货/已完成订单可申请）。"

        # --- 硬中断：挂起图执行，SSE 层把 payload 推给前端渲染确认卡片 ---
        approved = interrupt({
            "action": "submit_aftersale",
            "order_no": order.get("orderNo"),
            "items": _item_names(order),
            "type": type,
            "type_text": _AFTERSALE_TYPE.get(type),
            "refund_amount": str(order.get("payAmount")),
            "reason": reason,
        })

        session_id = _current_session_id(config)
        params = {"order_no": order_no, "type": type, "reason": reason}
        if not approved:
            await write_audit(
                user_id=user_id, session_id=session_id, tool_name="submit_aftersale",
                order_no=order_no, params=params, result="rejected", detail="用户拒绝确认",
            )
            return "用户已取消该售后申请，请告知用户申请未提交。"

        # --- 用户已确认：执行写库 ---
        try:
            resp = await request_internal(
                "POST", f"{settings.ORDER_SERVICE_URL}/api/v1/aftersale/apply",
                params={"userId": user_id},
                json={"orderNo": order_no, "type": type, "reason": reason},
            )
            body = resp.json()
        except Exception as e:
            logger.warning("提交售后申请失败 order_no=%s: %s", order_no, e)
            await write_audit(
                user_id=user_id, session_id=session_id, tool_name="submit_aftersale",
                order_no=order_no, params=params, result="failed", detail=f"HTTP异常: {e}",
            )
            raise ToolError(f"提交售后申请时出错: {e}")

        if resp.status_code != 200 or body.get("code") != 200:
            await write_audit(
                user_id=user_id, session_id=session_id, tool_name="submit_aftersale",
                order_no=order_no, params=params, result="failed",
                detail=body.get("message", "未知错误"),
            )
            raise ToolError(f"售后申请失败: {body.get('message', '未知错误')}")

        data = body.get("data") or {}
        await write_audit(
            user_id=user_id, session_id=session_id, tool_name="submit_aftersale",
            order_no=order_no, params=params, result="success",
            detail=f"售后单号 {data.get('aftersaleNo')}，退款 ¥{data.get('refundAmount')}",
        )
        if data.get("type") == 1:
            return (
                f"仅退款申请已完成，退款 ¥{data.get('refundAmount')} 已原路退回，"
                f"售后单号 {data.get('aftersaleNo')}。"
            )
        return (
            f"退货退款申请已审核通过（售后单号 {data.get('aftersaleNo')}）。"
            "请告知用户将商品寄回退货地址；用户表示已寄回后，"
            "调用 complete_return_refund 完成签收退款。"
        )

    return await timed_call("submit_aftersale", _run, service="订单服务")


@tool
async def complete_return_refund(
    config: RunnableConfig,
    order_no: str,
) -> str:
    """用户已寄回退货商品后调用，模拟仓库签收并完成退款（写操作）。
    系统会自动暂停并向用户展示确认卡片，用户点击确认后才真正执行。

    Args:
        order_no: 售后单对应的原订单号（工具自动查找该订单待寄回的退货退款单）
    """

    async def _run() -> str:
        user_id = _current_user_id(config)
        if not user_id:
            return "当前未登录，无法操作。请先登录后再试。"

        # --- 只读定位待寄回的退货退款单（interrupt 恢复后重跑，保持幂等） ---
        try:
            list_resp = await request_internal(
                "GET", f"{settings.ORDER_SERVICE_URL}/api/v1/aftersale/order/{order_no}",
                params={"userId": user_id},
            )
            list_body = list_resp.json()
        except Exception as e:
            logger.warning("查询售后记录失败 order_no=%s: %s", order_no, e)
            raise ToolError(f"查询售后记录时出错: {e}")

        if list_resp.status_code != 200 or list_body.get("code") != 200:
            raise ToolError(f"查询售后记录失败: {list_body.get('message', '未知错误')}")

        target = next(
            (row for row in (list_body.get("data") or [])
             if row.get("type") == 2 and row.get("status") == 1),
            None,
        )
        if not target:
            return "未找到该订单待处理的退货退款单（可能已完成）。"

        # --- 硬中断：向用户确认签收退款 ---
        approved = interrupt({
            "action": "complete_return_refund",
            "order_no": order_no,
            "items": f"售后单 {target.get('aftersaleNo')}",
            "type": 2,
            "type_text": "退货退款（签收并退款）",
            "refund_amount": str(target.get("refundAmount")),
            "reason": "用户已寄回商品，仓库签收后原路退款",
        })

        session_id = _current_session_id(config)
        params = {"order_no": order_no, "aftersale_id": target.get("id")}
        if not approved:
            await write_audit(
                user_id=user_id, session_id=session_id, tool_name="complete_return_refund",
                order_no=order_no, params=params, result="rejected", detail="用户拒绝确认",
            )
            return "用户已取消签收退款操作，请告知用户退款未执行。"

        # --- 用户已确认：执行签收退款 ---
        try:
            resp = await request_internal(
                "POST", f"{settings.ORDER_SERVICE_URL}/api/v1/aftersale/"
                f"{target.get('id')}/refund",
                params={"userId": user_id},
            )
            body = resp.json()
        except Exception as e:
            logger.warning("完成退货退款失败 order_no=%s: %s", order_no, e)
            await write_audit(
                user_id=user_id, session_id=session_id, tool_name="complete_return_refund",
                order_no=order_no, params=params, result="failed", detail=f"HTTP异常: {e}",
            )
            raise ToolError(f"操作时出错: {e}")

        if resp.status_code != 200 or body.get("code") != 200:
            await write_audit(
                user_id=user_id, session_id=session_id, tool_name="complete_return_refund",
                order_no=order_no, params=params, result="failed",
                detail=body.get("message", "未知错误"),
            )
            raise ToolError(f"操作失败: {body.get('message', '未知错误')}")

        data = body.get("data") or {}
        await write_audit(
            user_id=user_id, session_id=session_id, tool_name="complete_return_refund",
            order_no=order_no, params=params, result="success",
            detail=f"售后单 {data.get('aftersaleNo')} 已完成，退款 ¥{data.get('refundAmount')}",
        )
        return (
            f"仓库已签收，退款 ¥{data.get('refundAmount')} 已原路退回，"
            f"售后单 {data.get('aftersaleNo')} 已完成。"
        )

    return await timed_call("complete_return_refund", _run, service="订单服务")
