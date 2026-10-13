"""商品域工具：搜索与详情（经 product-service 内部接口）。

search_products / get_product_detail 成功时返回 JSON 字符串（顶层统一为
"products" 数组），SSE 层据此解析出 product_card 事件；失败返回可读错误文本。
"""
import json

from langchain_core.tools import tool

from app.core.config import settings
from app.core.http_client import request_internal
from app.tools.base import ToolError, timed_call


def _product_card(p: dict) -> dict:
    """Java 商品记录 → 前端卡片字段（SSE product_card 依赖该结构）。"""
    return {
        "id": p.get("id"),
        "name": p.get("productName", ""),
        "price": p.get("price"),
        "original_price": p.get("originalPrice"),
        "sales": p.get("sales", 0),
        "image": p.get("mainImage", ""),
    }


@tool
async def search_products(keyword: str, category: str = "", page: int = 1,
                          page_size: int = 5) -> str:
    """根据关键词搜索在售商品，返回商品列表。当用户没有指定具体商品ID、或想浏览/比较商品时使用。

    Args:
        keyword: 搜索关键词，如"手机"、"耳机"、"笔记本电脑"
        category: 商品分类ID（数字字符串），可选，用于限定分类
        page: 页码，从 1 开始，默认第 1 页
        page_size: 每页返回数量，默认 5
    """

    async def _run() -> str:
        params: dict = {"keyword": keyword, "pageNum": page, "pageSize": page_size}
        if category:
            params["categoryId"] = category
        resp = await request_internal(
            "GET", f"{settings.PRODUCT_SERVICE_URL}/api/v1/products", params=params
        )
        if resp.status_code != 200:
            raise ToolError(f"搜索商品失败: HTTP {resp.status_code}")
        records = (resp.json().get("data") or {}).get("records") or []
        products = [_product_card(p) for p in records]
        note = (
            f"共 {len(products)} 件与「{keyword}」相关的商品"
            if products else f"未找到与「{keyword}」相关的商品"
        )
        return json.dumps({"products": products, "note": note}, ensure_ascii=False)

    return await timed_call("search_products", _run, service="商品服务")


@tool
async def get_product_detail(product_id: str) -> str:
    """按商品ID查询商品详情与SKU规格（名称、价格、品牌、描述、各规格价格与库存）。
    用户询问某个具体商品的详细信息/规格/库存时使用；商品ID可从搜索结果获得。

    Args:
        product_id: 商品ID
    """

    async def _run() -> str:
        detail_resp = await request_internal(
            "GET", f"{settings.PRODUCT_SERVICE_URL}/api/v1/products/{product_id}"
        )
        if detail_resp.status_code != 200:
            raise ToolError(f"获取商品详情失败: HTTP {detail_resp.status_code}")
        data = detail_resp.json().get("data") or {}
        if not data:
            return json.dumps(
                {"products": [], "note": f"未找到商品ID={product_id}的信息"},
                ensure_ascii=False,
            )

        product = _product_card(data)
        # 详情文本字段附加（SSE 层只取顶层 products 出卡片，模型读全量字段作答）
        product.update({
            "brand_name": data.get("brandName", ""),
            "description": data.get("description", ""),
            "detail": (
                f"商品ID:{data.get('id')} | 名称:{data.get('productName')} | "
                f"价格:¥{data.get('price')} | 原价:¥{data.get('originalPrice') or data.get('price')} | "
                f"品牌:{data.get('brandName', 'N/A')} | 描述:{data.get('description', 'N/A')} | "
                f"销量:{data.get('sales', 0)}"
            ),
        })

        # SKU 列表为附加信息：失败不影响详情返回
        skus: list[dict] = []
        try:
            sku_resp = await request_internal(
                "GET", f"{settings.PRODUCT_SERVICE_URL}/api/v1/products/{product_id}/skus"
            )
            if sku_resp.status_code == 200:
                skus = [
                    {"id": s.get("id"), "sku_name": s.get("skuName", ""),
                     "price": s.get("price"), "stock": s.get("stock")}
                    for s in (sku_resp.json().get("data") or [])
                ]
        except Exception as e:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).warning(
                "查询SKU列表失败(忽略) product_id=%s: %s", product_id, e
            )

        return json.dumps(
            {"products": [product], "skus": skus, "note": "商品详情与SKU规格"},
            ensure_ascii=False,
        )

    return await timed_call("get_product_detail", _run, service="商品服务")
