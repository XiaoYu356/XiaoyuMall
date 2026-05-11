from agents.base_agent import BaseAgent
from typing import Any, Dict
import httpx
from config.settings import settings
from datetime import datetime
import random


class PriceAnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="价格分析专家",
            role="价格分析师",
            goal="分析商品价格趋势、历史价格、性价比，帮助用户找到最佳购买时机",
            backstory="""你是一位资深的价格分析师，拥有丰富的市场定价经验。
            你精通价格趋势分析、竞品价格对比、促销时机预测。
            你能够帮助用户判断当前价格是否合理，预测未来价格走势，找到最佳购买时机。"""
        )
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        product_id = context.get("product_id")
        product_info = context.get("product_info", {})
        
        price_analysis = await self._analyze_price(product_id, product_info)
        
        return {
            "agent": self.name,
            "product_id": product_id,
            "price_analysis": price_analysis
        }
    
    async def _analyze_price(self, product_id: str, product_info: Dict) -> Dict:
        current_price = product_info.get("price", 999.00)
        original_price = product_info.get("originalPrice", current_price)
        
        price_history = await self._get_price_history(product_id)
        competitor_prices = await self._get_competitor_prices(product_id)
        
        discount_rate = (original_price - current_price) / original_price if original_price > 0 else 0
        
        price_trend = self._analyze_trend(price_history)
        
        buy_recommendation = self._generate_buy_recommendation(
            current_price, original_price, discount_rate, price_trend
        )
        
        return {
            "current_price": current_price,
            "original_price": original_price,
            "discount_rate": round(discount_rate * 100, 2),
            "price_trend": price_trend,
            "price_history": price_history,
            "competitor_prices": competitor_prices,
            "buy_recommendation": buy_recommendation,
            "best_buy_time": "现在" if discount_rate > 0.2 else "建议等待促销"
        }
    
    async def _get_price_history(self, product_id: str) -> list:
        base_price = 999.00
        history = []
        for i in range(30):
            days_ago = 30 - i
            price = base_price * (1 + random.uniform(-0.1, 0.1))
            history.append({
                "date": (datetime.now() - __import__('datetime').timedelta(days=days_ago)).strftime("%Y-%m-%d"),
                "price": round(price, 2)
            })
        return history
    
    async def _get_competitor_prices(self, product_id: str) -> list:
        base_price = 999.00
        return [
            {"platform": "京东", "price": round(base_price * 1.05, 2)},
            {"platform": "天猫", "price": round(base_price * 0.98, 2)},
            {"platform": "拼多多", "price": round(base_price * 0.95, 2)}
        ]
    
    def _analyze_trend(self, price_history: list) -> str:
        if len(price_history) < 2:
            return "稳定"
        
        recent_prices = [p["price"] for p in price_history[-7:]]
        older_prices = [p["price"] for p in price_history[:7]]
        
        recent_avg = sum(recent_prices) / len(recent_prices)
        older_avg = sum(older_prices) / len(older_prices)
        
        if recent_avg < older_avg * 0.95:
            return "下降"
        elif recent_avg > older_avg * 1.05:
            return "上升"
        else:
            return "稳定"
    
    def _generate_buy_recommendation(
        self,
        current_price: float,
        original_price: float,
        discount_rate: float,
        trend: str
    ) -> str:
        if discount_rate > 0.3:
            return "强烈推荐购买，当前折扣力度很大"
        elif discount_rate > 0.2:
            return "推荐购买，价格优惠较多"
        elif discount_rate > 0.1:
            return "可以考虑购买，有一定优惠"
        elif trend == "下降":
            return "建议继续观望，价格呈下降趋势"
        else:
            return "价格适中，可以购买"
