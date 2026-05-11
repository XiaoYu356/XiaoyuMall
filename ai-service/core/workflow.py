from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END


class WorkflowState(TypedDict):
    product_id: str
    user_id: str
    user_query: str
    product_info: dict
    product_analysis: dict
    price_analysis: dict
    coupon_strategy: dict
    recommendation: dict
    current_step: str


class ShoppingAssistantWorkflow:
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.graph = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph(WorkflowState)
        
        workflow.add_node("fetch_product", self._fetch_product_node)
        workflow.add_node("analyze_product", self._analyze_product_node)
        workflow.add_node("analyze_price", self._analyze_price_node)
        workflow.add_node("find_coupons", self._find_coupons_node)
        workflow.add_node("generate_recommendation", self._generate_recommendation_node)
        
        workflow.set_entry_point("fetch_product")
        
        workflow.add_edge("fetch_product", "analyze_product")
        workflow.add_edge("analyze_product", "analyze_price")
        workflow.add_edge("analyze_product", "find_coupons")
        workflow.add_edge("analyze_price", "generate_recommendation")
        workflow.add_edge("find_coupons", "generate_recommendation")
        workflow.add_edge("generate_recommendation", END)
        
        return workflow.compile()
    
    async def _fetch_product_node(self, state: WorkflowState) -> dict:
        import asyncio
        context = {
            "product_id": state["product_id"]
        }
        result = await self.coordinator.product_agent.execute(context)
        return {
            "product_info": result.get("analysis", {}),
            "current_step": "fetch_product"
        }
    
    async def _analyze_product_node(self, state: WorkflowState) -> dict:
        context = {
            "product_id": state["product_id"],
            "product_info": state["product_info"]
        }
        result = await self.coordinator.product_agent.execute(context)
        return {
            "product_analysis": result.get("analysis", {}),
            "current_step": "analyze_product"
        }
    
    async def _analyze_price_node(self, state: WorkflowState) -> dict:
        context = {
            "product_id": state["product_id"],
            "product_info": state["product_info"]
        }
        result = await self.coordinator.price_agent.execute(context)
        return {
            "price_analysis": result.get("price_analysis", {}),
            "current_step": "analyze_price"
        }
    
    async def _find_coupons_node(self, state: WorkflowState) -> dict:
        context = {
            "user_id": state["user_id"],
            "product_id": state["product_id"],
            "order_amount": state["product_info"].get("price", 0)
        }
        result = await self.coordinator.coupon_agent.execute(context)
        return {
            "coupon_strategy": result.get("best_strategy", {}),
            "current_step": "find_coupons"
        }
    
    async def _generate_recommendation_node(self, state: WorkflowState) -> dict:
        context = {
            "product_analysis": state["product_analysis"],
            "price_analysis": state["price_analysis"],
            "coupon_strategy": state["coupon_strategy"],
            "user_query": state["user_query"]
        }
        result = await self.coordinator.recommendation_agent.execute(context)
        return {
            "recommendation": result.get("recommendation", {}),
            "current_step": "generate_recommendation"
        }
    
    async def run(self, product_id: str, user_id: str, user_query: str) -> dict:
        initial_state = {
            "product_id": product_id,
            "user_id": user_id,
            "user_query": user_query,
            "product_info": {},
            "product_analysis": {},
            "price_analysis": {},
            "coupon_strategy": {},
            "recommendation": {},
            "current_step": "start"
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        return final_state
