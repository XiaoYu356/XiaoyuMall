from typing import Dict, Any, List
from agents import (
    ProductAnalystAgent,
    PriceAnalystAgent,
    CouponExpertAgent,
    RecommendationAdvisorAgent
)
import asyncio
from datetime import datetime


class AgentCoordinator:
    def __init__(self):
        self.product_agent = ProductAnalystAgent()
        self.price_agent = PriceAnalystAgent()
        self.coupon_agent = CouponExpertAgent()
        self.recommendation_agent = RecommendationAdvisorAgent()
        
        self.execution_history: List[Dict[str, Any]] = []
    
    async def analyze_and_recommend(
        self,
        product_id: str,
        user_id: str,
        user_query: str
    ) -> Dict[str, Any]:
        start_time = datetime.now()
        
        context = {
            "product_id": product_id,
            "user_id": user_id,
            "user_query": user_query
        }
        
        product_result = await self.product_agent.execute(context)
        context["product_info"] = product_result.get("analysis", {})
        context["order_amount"] = product_result.get("analysis", {}).get("price", 999)
        
        price_task = self.price_agent.execute(context)
        coupon_task = self.coupon_agent.execute(context)
        
        price_result, coupon_result = await asyncio.gather(
            price_task, coupon_task
        )
        
        context["product_analysis"] = product_result.get("analysis", {})
        context["price_analysis"] = price_result.get("price_analysis", {})
        context["coupon_strategy"] = coupon_result.get("best_strategy", {})
        
        recommendation_result = await self.recommendation_agent.execute(context)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        final_result = {
            "success": True,
            "execution_time": round(execution_time, 2),
            "agents_involved": [
                self.product_agent.name,
                self.price_agent.name,
                self.coupon_agent.name,
                self.recommendation_agent.name
            ],
            "product_analysis": product_result,
            "price_analysis": price_result,
            "coupon_analysis": coupon_result,
            "recommendation": recommendation_result.get("recommendation", {}),
            "timestamp": datetime.now().isoformat()
        }
        
        self.execution_history.append(final_result)
        
        return final_result
    
    async def quick_analysis(self, product_id: str) -> Dict[str, Any]:
        context = {"product_id": product_id}
        
        product_result = await self.product_agent.execute(context)
        
        return {
            "success": True,
            "product_id": product_id,
            "product_analysis": product_result.get("analysis", {})
        }
    
    async def price_check(self, product_id: str) -> Dict[str, Any]:
        context = {"product_id": product_id}
        
        price_result = await self.price_agent.execute(context)
        
        return {
            "success": True,
            "product_id": product_id,
            "price_analysis": price_result.get("price_analysis", {})
        }
    
    async def find_best_coupon(
        self,
        user_id: str,
        order_amount: float
    ) -> Dict[str, Any]:
        context = {
            "user_id": user_id,
            "order_amount": order_amount
        }
        
        coupon_result = await self.coupon_agent.execute(context)
        
        return {
            "success": True,
            "user_id": user_id,
            "best_strategy": coupon_result.get("best_strategy", {})
        }
    
    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.execution_history[-limit:]
