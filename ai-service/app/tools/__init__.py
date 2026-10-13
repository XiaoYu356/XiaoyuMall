"""五域工具集合（11 个），供 graph builder 挂载到单 Agent。

- 商品域：search_products / get_product_detail（返回 JSON，SSE 出 product_card）
- 优惠域：get_available_coupons / calculate_coupon_discount / get_my_coupons
- 订单域：get_my_orders / get_order_detail / get_logistics_timeline
- 售后域：submit_aftersale / complete_return_refund（HITL 写操作）
- 知识域：search_faq（agentic RAG，返回 JSON，SSE 出 citation）
"""
from app.tools.aftersale_tools import complete_return_refund, submit_aftersale
from app.tools.coupon_tools import (
    calculate_coupon_discount,
    get_available_coupons,
    get_my_coupons,
)
from app.tools.faq_tools import search_faq
from app.tools.order_tools import (
    get_logistics_timeline,
    get_my_orders,
    get_order_detail,
)
from app.tools.product_tools import get_product_detail, search_products

ALL_TOOLS = [
    # 商品域
    search_products,
    get_product_detail,
    # 优惠域
    get_available_coupons,
    calculate_coupon_discount,
    get_my_coupons,
    # 订单域
    get_my_orders,
    get_order_detail,
    get_logistics_timeline,
    # 售后域
    submit_aftersale,
    complete_return_refund,
    # 知识域
    search_faq,
]
