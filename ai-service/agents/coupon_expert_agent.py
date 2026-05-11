from agents.base_agent import BaseAgent
from typing import Any, Dict
import httpx
from config.settings import settings


class CouponExpertAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="优惠券专家",
            role="优惠券分析师",
            goal="查找可用优惠券、计算最优优惠方案，帮助用户最大化节省开支",
            backstory="""你是一位优惠券专家，精通各类电商平台的优惠规则和叠加策略。
            你能够快速找到最适合用户的优惠券，计算最优的优惠组合方案。
            你熟悉满减、折扣、现金券等各类优惠券的使用规则和最佳使用时机。"""
        )
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        product_id = context.get("product_id")
        user_id = context.get("user_id")
        order_amount = context.get("order_amount", 0)
        
        available_coupons = await self._fetch_available_coupons(user_id, product_id)
        
        best_strategy = self._calculate_best_strategy(available_coupons, order_amount)
        
        return {
            "agent": self.name,
            "product_id": product_id,
            "user_id": user_id,
            "available_coupons": available_coupons,
            "best_strategy": best_strategy
        }
    
    async def _fetch_available_coupons(self, user_id: str, product_id: str) -> list:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{settings.COUPON_SERVICE_URL}/api/v1/coupons/user/{user_id}",
                    params={"status": 0}
                )
                if response.status_code == 200:
                    return response.json().get("data", {}).get("records", [])
            except Exception as e:
                print(f"获取优惠券失败: {e}")
        
        return [
            {
                "id": 1,
                "couponCode": "CPN100",
                "couponType": 1,
                "couponValue": 100,
                "minAmount": 500,
                "templateName": "满500减100"
            },
            {
                "id": 2,
                "couponCode": "CPN50",
                "couponType": 1,
                "couponValue": 50,
                "minAmount": 300,
                "templateName": "满300减50"
            },
            {
                "id": 3,
                "couponCode": "CPN85",
                "couponType": 2,
                "couponValue": 8.5,
                "minAmount": 0,
                "templateName": "全场85折券"
            }
        ]
    
    def _calculate_best_strategy(self, coupons: list, order_amount: float) -> Dict:
        if not coupons:
            return {
                "recommendation": "暂无可用优惠券",
                "best_coupon": None,
                "max_discount": 0,
                "final_price": order_amount
            }
        
        best_coupon = None
        max_discount = 0
        
        for coupon in coupons:
            coupon_type = coupon.get("couponType")
            coupon_value = coupon.get("couponValue", 0)
            min_amount = coupon.get("minAmount", 0)
            
            if order_amount < min_amount:
                continue
            
            if coupon_type == 1:
                discount = coupon_value
            elif coupon_type == 2:
                discount = order_amount * (1 - coupon_value / 10)
            elif coupon_type == 3:
                discount = coupon_value
            else:
                discount = 0
            
            if discount > max_discount:
                max_discount = discount
                best_coupon = coupon
        
        if best_coupon:
            return {
                "recommendation": f"推荐使用【{best_coupon.get('templateName')}】，可节省¥{max_discount:.2f}",
                "best_coupon": best_coupon,
                "max_discount": round(max_discount, 2),
                "final_price": round(order_amount - max_discount, 2)
            }
        else:
            return {
                "recommendation": f"当前订单金额不满足优惠券使用条件，建议凑单至¥{min(c['minAmount'] for c in coupons)}",
                "best_coupon": None,
                "max_discount": 0,
                "final_price": order_amount
            }
