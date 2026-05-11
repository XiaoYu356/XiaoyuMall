# 智能百货平台 - 多智能体购物助手服务

## 项目简介

基于多智能体协作的智能购物助手系统，为用户提供商品分析、价格评估、优惠推荐等智能服务。

## 技术栈

- **Python 3.11**
- **FastAPI** - 高性能Web框架
- **LangChain** - LLM应用开发框架
- **LangGraph** - 多智能体工作流编排
- **OpenAI API** - 大语言模型接口

## 项目结构

```
ai-service/
├── agents/                 # 智能体模块
│   ├── base_agent.py      # 基础智能体类
│   ├── product_analyst_agent.py    # 商品分析智能体
│   ├── price_analyst_agent.py      # 价格分析智能体
│   ├── coupon_expert_agent.py      # 优惠券专家智能体
│   └── recommendation_advisor_agent.py  # 推荐顾问智能体
├── core/                   # 核心模块
│   ├── coordinator.py     # 智能体协调器
│   └── workflow.py        # 工作流编排
├── api/                    # API接口
│   ├── routes.py          # 路由定义
│   └── schemas.py         # 数据模型
├── config/                 # 配置模块
│   └── settings.py        # 配置管理
├── main.py                 # 应用入口
├── requirements.txt        # 依赖列表
├── Dockerfile              # Docker配置
└── .env.example            # 环境变量示例
```

## 多智能体架构

```
用户请求
    │
    ▼
┌──────────────────┐
│   协调器          │
│ (Coordinator)     │
└──────────────────┘
    │
    ├─────────────────┬─────────────────┐
    ▼                 ▼                 ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│ 商品分析 │   │ 价格分析 │   │ 优惠券专家│
│  Agent   │   │  Agent   │   │  Agent   │
└──────────┘   └──────────┘   └──────────┘
    │                 │                 │
    └─────────────────┼─────────────────┘
                      ▼
            ┌──────────────────┐
            │   推荐顾问        │
            │     Agent        │
            └──────────────────┘
                      │
                      ▼
                最终推荐结果
```

## 智能体说明

### 1. 商品分析智能体 (ProductAnalystAgent)
- **角色**: 商品分析师
- **职责**: 分析商品特点、品质、适用场景
- **输出**: 商品分析报告

### 2. 价格分析智能体 (PriceAnalystAgent)
- **角色**: 价格分析师
- **职责**: 分析价格趋势、历史价格、性价比
- **输出**: 价格分析报告

### 3. 优惠券专家智能体 (CouponExpertAgent)
- **角色**: 优惠券分析师
- **职责**: 查找可用优惠券、计算最优优惠方案
- **输出**: 最优优惠策略

### 4. 推荐顾问智能体 (RecommendationAdvisorAgent)
- **角色**: 购物顾问
- **职责**: 综合分析给出购买建议
- **输出**: 综合推荐报告

## API接口

### 1. 完整分析接口
```http
POST /api/v1/ai/analyze
Content-Type: application/json

{
  "product_id": "1",
  "user_id": "1",
  "user_query": "我想买一款性价比高的手机"
}
```

### 2. 商品分析接口
```http
POST /api/v1/ai/analyze/product
Content-Type: application/json

{
  "product_id": "1"
}
```

### 3. 价格分析接口
```http
POST /api/v1/ai/analyze/price
Content-Type: application/json

{
  "product_id": "1"
}
```

### 4. 优惠券分析接口
```http
POST /api/v1/ai/analyze/coupon
Content-Type: application/json

{
  "user_id": "1",
  "order_amount": 999.00
}
```

### 5. 工作流分析接口
```http
POST /api/v1/ai/workflow/analyze
Content-Type: application/json

{
  "product_id": "1",
  "user_id": "1",
  "user_query": "帮我分析这款商品"
}
```

### 6. 健康检查接口
```http
GET /api/v1/ai/health
```

## 快速开始

### 1. 安装依赖
```bash
cd ai-service
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，配置OpenAI API Key等
```

### 3. 启动服务
```bash
python main.py
```

### 4. 访问API文档
```
http://localhost:8000/docs
```

## Docker部署

### 1. 构建镜像
```bash
docker build -t mall-ai-service .
```

### 2. 运行容器
```bash
docker run -d \
  --name ai-service \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your-api-key \
  mall-ai-service
```

### 3. 使用Docker Compose
```bash
cd backend
docker-compose up -d ai-service
```

## 与Spring Cloud集成

AI服务已集成到Spring Cloud微服务架构中：

1. **服务注册**: 通过Nacos进行服务注册与发现
2. **服务调用**: Java服务通过HTTP调用AI服务接口
3. **配置管理**: 通过环境变量配置服务地址

### Java服务调用示例

```java
@FeignClient(name = "ai-service", url = "${ai.service.url}")
public interface AIServiceClient {
    
    @PostMapping("/api/v1/ai/analyze")
    AIAnalysisResult analyzeProduct(@RequestBody AIAnalysisRequest request);
}
```

## 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| OPENAI_API_KEY | OpenAI API密钥 | - |
| OPENAI_API_BASE | OpenAI API地址 | https://api.openai.com/v1 |
| OPENAI_MODEL | 使用的模型 | gpt-3.5-turbo |
| REDIS_HOST | Redis主机 | localhost |
| REDIS_PORT | Redis端口 | 6379 |
| PRODUCT_SERVICE_URL | 商品服务地址 | http://localhost:8081 |
| COUPON_SERVICE_URL | 优惠券服务地址 | http://localhost:8082 |

## 扩展开发

### 添加新的智能体

1. 创建新的智能体类，继承`BaseAgent`
2. 实现`execute`方法
3. 在`coordinator.py`中注册智能体
4. 在工作流中添加节点

示例：

```python
from agents.base_agent import BaseAgent

class CustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="自定义智能体",
            role="自定义角色",
            goal="自定义目标",
            backstory="自定义背景"
        )
    
    async def execute(self, context):
        # 实现自定义逻辑
        return {"result": "分析结果"}
```

## 注意事项

1. **API密钥安全**: 请妥善保管OpenAI API密钥，不要提交到代码仓库
2. **成本控制**: 合理使用LLM接口，避免不必要的调用
3. **错误处理**: 生产环境请添加完善的错误处理和日志记录
4. **性能优化**: 考虑添加缓存机制，减少重复分析

## License

MIT License
