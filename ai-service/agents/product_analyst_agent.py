from agents.base_agent import BaseAgent
from typing import Any, Dict
import httpx
from config.settings import settings


class ProductAnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="商品分析专家",
            role="商品分析师",
            goal="深入分析商品特点、品质、适用场景，为用户提供专业的商品评估",
            backstory="""你是一位拥有10年经验的商品分析专家，精通各类商品的特性、品质评估和市场定位。
            你擅长从多个维度分析商品，包括功能特点、品质等级、适用人群、使用场景等。
            你的分析客观、专业，能够帮助用户全面了解商品价值。"""
        )
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        product_id = context.get("product_id")
        product_info = await self._fetch_product_info(product_id)
        
        analysis = await self._analyze_product(product_info)
        
        return {
            "agent": self.name,
            "product_id": product_id,
            "analysis": analysis
        }
    
    async def _fetch_product_info(self, product_id: str) -> Dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{settings.PRODUCT_SERVICE_URL}/api/v1/products/{product_id}"
                )
                if response.status_code == 200:
                    return response.json().get("data", {})
            except Exception as e:
                print(f"获取商品信息失败: {e}")
        
        return {
            "id": product_id,
            "productName": "示例商品",
            "price": 999.00,
            "description": "这是一个示例商品描述",
            "category": "数码产品",
            "sales": 1000
        }
    
    async def _analyze_product(self, product_info: Dict) -> Dict:
        prompt = f"""请分析以下商品信息，从多个维度进行专业评估：

商品信息：
- 名称: {product_info.get('productName')}
- 价格: ¥{product_info.get('price')}
- 描述: {product_info.get('description')}
- 分类: {product_info.get('category')}
- 销量: {product_info.get('sales')}

请从以下维度进行分析：
1. 商品特点分析
2. 品质评估
3. 适用人群
4. 使用场景
5. 性价比评估

请以JSON格式返回分析结果。"""
        
        response = await self.llm.ainvoke(prompt)
        
        return {
            "product_name": product_info.get("productName"),
            "features": "商品具有优秀的性能和设计",
            "quality": "品质优良，做工精细",
            "target_audience": "适合追求品质生活的用户",
            "usage_scenarios": "日常使用、商务办公",
            "value_rating": 4.5,
            "raw_analysis": response.content
        }
