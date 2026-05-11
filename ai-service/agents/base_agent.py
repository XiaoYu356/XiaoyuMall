from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from langchain_openai import ChatOpenAI
from config.settings import settings


class BaseAgent(ABC):
    def __init__(
        self,
        name: str,
        role: str,
        goal: str,
        backstory: str,
        model: Optional[str] = None
    ):
        self.name = name
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.model = model or settings.OPENAI_MODEL
        self.llm = self._init_llm()
    
    def _init_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.model,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
            temperature=0.7
        )
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    def get_system_prompt(self) -> str:
        return f"""你是一个{self.role}。

你的目标是: {self.goal}

你的背景: {self.backstory}

请根据你的角色和专业知识，完成分配给你的任务。"""
    
    def __repr__(self) -> str:
        return f"<{self.name}: {self.role}>"
