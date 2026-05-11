from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AnalysisRequest(BaseModel):
    product_id: str = Field(..., description="商品ID")
    user_id: str = Field(..., description="用户ID")
    user_query: str = Field(..., description="用户查询内容")


class QuickAnalysisRequest(BaseModel):
    product_id: str = Field(..., description="商品ID")


class CouponRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    order_amount: float = Field(..., description="订单金额")


class AnalysisResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ProductAnalysis(BaseModel):
    product_name: str
    features: str
    quality: str
    target_audience: str
    usage_scenarios: str
    value_rating: float


class PriceAnalysis(BaseModel):
    current_price: float
    original_price: float
    discount_rate: float
    price_trend: str
    buy_recommendation: str
    best_buy_time: str


class CouponStrategy(BaseModel):
    recommendation: str
    best_coupon: Optional[Dict[str, Any]] = None
    max_discount: float
    final_price: float


class Recommendation(BaseModel):
    product_name: str
    current_price: float
    final_price: float
    total_savings: float
    overall_score: int
    buy_recommendation: str
    detailed_analysis: str
    summary: Dict[str, str]


class FullAnalysisResponse(BaseModel):
    success: bool
    execution_time: float
    agents_involved: List[str]
    product_analysis: Dict[str, Any]
    price_analysis: Dict[str, Any]
    coupon_analysis: Dict[str, Any]
    recommendation: Recommendation
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
