import json
from typing import AsyncGenerator, Dict, Any
from datetime import datetime
import asyncio


class StreamingCoordinator:
    def __init__(self, coordinator):
        self.coordinator = coordinator
    
    async def stream_analysis(
        self,
        product_id: str,
        user_id: str,
        user_query: str
    ) -> AsyncGenerator[str, None]:
        yield self._format_event("start", {
            "message": "开始分析",
            "timestamp": datetime.now().isoformat()
        })
        
        yield self._format_event("agent_start", {
            "agent": self.coordinator.product_agent.name,
            "role": self.coordinator.product_agent.role,
            "message": "商品分析专家开始工作..."
        })
        
        product_result = await self.coordinator.product_agent.execute({
            "product_id": product_id
        })
        
        yield self._format_event("agent_complete", {
            "agent": self.coordinator.product_agent.name,
            "result": product_result.get("analysis", {}),
            "message": "商品分析完成"
        })
        
        yield self._format_event("agent_start", {
            "agent": self.coordinator.price_agent.name,
            "role": self.coordinator.price_agent.role,
            "message": "价格分析专家开始工作..."
        })
        
        price_result = await self.coordinator.price_agent.execute({
            "product_id": product_id,
            "product_info": product_result.get("analysis", {})
        })
        
        yield self._format_event("agent_complete", {
            "agent": self.coordinator.price_agent.name,
            "result": price_result.get("price_analysis", {}),
            "message": "价格分析完成"
        })
        
        yield self._format_event("agent_start", {
            "agent": self.coordinator.coupon_agent.name,
            "role": self.coordinator.coupon_agent.role,
            "message": "优惠券专家开始工作..."
        })
        
        coupon_result = await self.coordinator.coupon_agent.execute({
            "user_id": user_id,
            "product_id": product_id,
            "order_amount": product_result.get("analysis", {}).get("price", 999)
        })
        
        yield self._format_event("agent_complete", {
            "agent": self.coordinator.coupon_agent.name,
            "result": coupon_result.get("best_strategy", {}),
            "message": "优惠券分析完成"
        })
        
        yield self._format_event("agent_start", {
            "agent": self.coordinator.recommendation_agent.name,
            "role": self.coordinator.recommendation_agent.role,
            "message": "推荐顾问开始综合分析..."
        })
        
        recommendation_result = await self.coordinator.recommendation_agent.execute({
            "product_analysis": product_result.get("analysis", {}),
            "price_analysis": price_result.get("price_analysis", {}),
            "coupon_strategy": coupon_result.get("best_strategy", {}),
            "user_query": user_query
        })
        
        yield self._format_event("agent_complete", {
            "agent": self.coordinator.recommendation_agent.name,
            "result": recommendation_result.get("recommendation", {}),
            "message": "推荐分析完成"
        })
        
        final_result = {
            "success": True,
            "product_id": product_id,
            "user_id": user_id,
            "product_analysis": product_result.get("analysis", {}),
            "price_analysis": price_result.get("price_analysis", {}),
            "coupon_strategy": coupon_result.get("best_strategy", {}),
            "recommendation": recommendation_result.get("recommendation", {}),
            "timestamp": datetime.now().isoformat()
        }
        
        yield self._format_event("complete", final_result)
    
    async def stream_llm_response(
        self,
        product_id: str,
        user_query: str
    ) -> AsyncGenerator[str, None]:
        yield self._format_event("start", {
            "message": "开始AI分析",
            "timestamp": datetime.now().isoformat()
        })
        
        context = {
            "product_id": product_id,
            "user_query": user_query
        }
        
        product_result = await self.coordinator.product_agent.execute(context)
        
        yield self._format_event("data", {
            "type": "product_info",
            "data": product_result.get("analysis", {})
        })
        
        prompt = f"""作为购物助手，请根据以下信息回答用户问题：

用户问题: {user_query}

商品信息: {json.dumps(product_result.get("analysis", {}), ensure_ascii=False)}

请给出专业的购买建议。"""
        
        async for chunk in self._stream_llm(prompt):
            yield self._format_event("llm_chunk", {
                "content": chunk
            })
        
        yield self._format_event("complete", {
            "message": "分析完成",
            "timestamp": datetime.now().isoformat()
        })
    
    async def _stream_llm(self, prompt: str) -> AsyncGenerator[str, None]:
        try:
            from langchain_openai import ChatOpenAI
            
            llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                streaming=True,
                temperature=0.7
            )
            
            async for chunk in llm.astream(prompt):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            yield f"\n[错误: {str(e)}]"
    
    def _format_event(self, event_type: str, data: Dict[str, Any]) -> str:
        return f"data: {json.dumps({'type': event_type, 'data': data}, ensure_ascii=False)}\n\n"
