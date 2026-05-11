from agents.base_agent import BaseAgent
from typing import Any, Dict, List


class RecommendationAdvisorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="推荐顾问",
            role="购物顾问",
            goal="综合分析商品、价格、优惠信息，为用户提供专业的购买建议",
            backstory="""你是一位资深购物顾问，拥有丰富的消费决策经验。
            你能够综合分析商品特点、价格趋势、优惠方案等多个维度，为用户提供个性化的购买建议。
            你的建议客观、专业，帮助用户做出明智的购物决策。"""
        )
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        product_analysis = context.get("product_analysis", {})
        price_analysis = context.get("price_analysis", {})
        coupon_strategy = context.get("coupon_strategy", {})
        user_query = context.get("user_query", "")
        
        recommendation = await self._generate_recommendation(
            product_analysis,
            price_analysis,
            coupon_strategy,
            user_query
        )
        
        return {
            "agent": self.name,
            "recommendation": recommendation
        }
    
    async def _generate_recommendation(
        self,
        product_analysis: Dict,
        price_analysis: Dict,
        coupon_strategy: Dict,
        user_query: str
    ) -> Dict:
        product_name = product_analysis.get("product_name", "商品")
        current_price = price_analysis.get("current_price", 0)
        discount_rate = price_analysis.get("discount_rate", 0)
        price_trend = price_analysis.get("price_trend", "稳定")
        buy_recommendation = price_analysis.get("buy_recommendation", "")
        
        best_coupon = coupon_strategy.get("best_coupon")
        max_discount = coupon_strategy.get("max_discount", 0)
        final_price = coupon_strategy.get("final_price", current_price)
        
        overall_score = self._calculate_overall_score(
            product_analysis.get("value_rating", 3),
            discount_rate,
            max_discount,
            price_trend
        )
        
        prompt = f"""作为购物顾问，请根据以下信息为用户提供购买建议：

用户需求: {user_query}

商品分析:
- 商品名称: {product_name}
- 商品特点: {product_analysis.get('features', '优秀')}
- 品质评估: {product_analysis.get('quality', '优良')}
- 适用人群: {product_analysis.get('target_audience', '通用')}
- 性价比评分: {product_analysis.get('value_rating', 3)}/5

价格分析:
- 当前价格: ¥{current_price}
- 折扣力度: {discount_rate}%
- 价格趋势: {price_trend}
- 购买建议: {buy_recommendation}

优惠方案:
- 最佳优惠券: {best_coupon.get('templateName') if best_coupon else '无'}
- 优惠金额: ¥{max_discount}
- 最终价格: ¥{final_price}

请生成一份综合购买建议报告，包括：
1. 商品评价总结
2. 价格分析总结
3. 优惠方案建议
4. 最终购买建议
5. 评分（1-10分）"""
        
        response = await self.llm.ainvoke(prompt)
        
        return {
            "product_name": product_name,
            "current_price": current_price,
            "final_price": final_price,
            "total_savings": round(current_price - final_price, 2),
            "overall_score": overall_score,
            "buy_recommendation": self._get_buy_action(overall_score),
            "detailed_analysis": response.content,
            "summary": {
                "product_quality": product_analysis.get("quality", "优良"),
                "price_rating": "优惠" if discount_rate > 20 else "适中",
                "coupon_benefit": f"可节省¥{max_discount}" if max_discount > 0 else "暂无优惠",
                "action": "立即购买" if overall_score >= 7 else "建议观望"
            }
        }
    
    def _calculate_overall_score(
        self,
        value_rating: float,
        discount_rate: float,
        max_discount: float,
        price_trend: str
    ) -> int:
        score = value_rating * 2
        
        if discount_rate > 30:
            score += 3
        elif discount_rate > 20:
            score += 2
        elif discount_rate > 10:
            score += 1
        
        if max_discount > 100:
            score += 2
        elif max_discount > 50:
            score += 1
        
        if price_trend == "下降":
            score -= 1
        elif price_trend == "上升":
            score += 1
        
        return min(max(int(score), 1), 10)
    
    def _get_buy_action(self, score: int) -> str:
        if score >= 9:
            return "强烈推荐购买，性价比极高"
        elif score >= 7:
            return "推荐购买，综合表现优秀"
        elif score >= 5:
            return "可以考虑购买，表现中规中矩"
        else:
            return "建议继续观望，等待更好时机"
