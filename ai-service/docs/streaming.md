# 流式输出功能说明

## 概述

多智能体购物助手系统现已支持**流式输出（Streaming Output）**，用户可以实时看到每个智能体的分析过程和结果，提升用户体验。

---

## 流式输出 vs 普通输出

### 普通输出
- 等待所有智能体完成分析后一次性返回结果
- 用户需要等待较长时间才能看到结果
- 适合批量处理场景

### 流式输出 ✨
- 每个智能体完成分析后立即推送结果
- 用户可以实时看到分析进度
- 更好的用户体验
- 适合交互式场景

---

## API接口

### 1. 流式完整分析

**接口**: `POST /api/v1/ai/stream/analyze`

**请求示例**:
```javascript
fetch('http://localhost:8000/api/v1/ai/stream/analyze', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        product_id: "1",
        user_id: "1",
        user_query: "我想买一款性价比高的手机"
    })
})
.then(response => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    function read() {
        return reader.read().then(({ done, value }) => {
            if (done) {
                console.log('分析完成');
                return;
            }
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            lines.forEach(line => {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.substring(6));
                    console.log('收到事件:', data);
                }
            });
            
            return read();
        });
    }
    
    return read();
});
```

**事件类型**:

| 事件类型 | 说明 | 数据示例 |
|---------|------|---------|
| `start` | 开始分析 | `{"message": "开始分析", "timestamp": "..."}` |
| `agent_start` | 智能体开始工作 | `{"agent": "商品分析专家", "message": "开始工作..."}` |
| `agent_complete` | 智能体完成工作 | `{"agent": "商品分析专家", "result": {...}}` |
| `complete` | 分析完成 | `{完整分析结果}` |

---

### 2. 流式AI对话

**接口**: `POST /api/v1/ai/stream/chat`

**请求示例**:
```javascript
fetch('http://localhost:8000/api/v1/ai/stream/chat', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        product_id: "1",
        user_id: "1",
        user_query: "这款手机怎么样？"
    })
})
.then(response => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    let fullContent = '';
    
    function read() {
        return reader.read().then(({ done, value }) => {
            if (done) {
                console.log('完整回复:', fullContent);
                return;
            }
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            lines.forEach(line => {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.substring(6));
                    
                    if (data.type === 'llm_chunk') {
                        fullContent += data.data.content;
                        console.log('实时内容:', data.data.content);
                    }
                }
            });
            
            return read();
        });
    }
    
    return read();
});
```

**事件类型**:

| 事件类型 | 说明 |
|---------|------|
| `start` | 开始分析 |
| `data` | 商品数据 |
| `llm_chunk` | LLM流式输出片段 |
| `complete` | 对话完成 |

---

## 前端集成示例

### Vue 3 示例

```vue
<template>
  <div>
    <button @click="startAnalysis">开始分析</button>
    <div v-for="(message, index) in messages" :key="index">
      <div :class="message.type">
        {{ message.content }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const messages = ref([])

async function startAnalysis() {
  const response = await fetch('http://localhost:8000/api/v1/ai/stream/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      product_id: '1',
      user_id: '1',
      user_query: '我想买一款性价比高的手机'
    })
  })
  
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    
    const chunk = decoder.decode(value)
    const lines = chunk.split('\n')
    
    lines.forEach(line => {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.substring(6))
        
        messages.value.push({
          type: data.type,
          content: JSON.stringify(data.data, null, 2)
        })
      }
    })
  }
}
</script>
```

### React 示例

```jsx
import { useState } from 'react'

function App() {
  const [messages, setMessages] = useState([])
  
  const startAnalysis = async () => {
    const response = await fetch('http://localhost:8000/api/v1/ai/stream/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_id: '1',
        user_id: '1',
        user_query: '我想买一款性价比高的手机'
      })
    })
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')
      
      lines.forEach(line => {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.substring(6))
          setMessages(prev => [...prev, data])
        }
      })
    }
  }
  
  return (
    <div>
      <button onClick={startAnalysis}>开始分析</button>
      {messages.map((msg, idx) => (
        <div key={idx} className={msg.type}>
          {JSON.stringify(msg.data, null, 2)}
        </div>
      ))}
    </div>
  )
}
```

---

## 在线演示

启动服务后，访问以下地址查看流式输出演示：

```
http://localhost:8000/demo
```

演示页面功能：
- ✅ 实时显示每个智能体的工作状态
- ✅ 流式显示AI对话内容
- ✅ 美观的UI界面
- ✅ JSON格式化显示

---

## 技术实现

### SSE (Server-Sent Events)

流式输出基于SSE技术实现：

**服务端**:
```python
from fastapi.responses import StreamingResponse

@router.post("/stream/analyze")
async def stream_analysis(request: AnalysisRequest):
    return StreamingResponse(
        streaming_coordinator.stream_analysis(
            product_id=request.product_id,
            user_id=request.user_id,
            user_query=request.user_query
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

**数据格式**:
```
data: {"type": "agent_start", "data": {...}}

data: {"type": "agent_complete", "data": {...}}

data: {"type": "complete", "data": {...}}
```

---

## 性能优化

### 1. 并行执行
多个智能体可以并行执行，减少总耗时：

```python
# 并行执行价格分析和优惠券分析
price_task = self.price_agent.execute(context)
coupon_task = self.coupon_agent.execute(context)

price_result, coupon_result = await asyncio.gather(
    price_task, coupon_task
)
```

### 2. 缓存优化
对商品信息等静态数据进行缓存：

```python
# 使用Redis缓存商品信息
if cached_product := await redis.get(f"product:{product_id}"):
    return cached_product
```

### 3. 超时控制
设置智能体执行超时：

```python
try:
    result = await asyncio.wait_for(
        agent.execute(context),
        timeout=30.0
    )
except asyncio.TimeoutError:
    yield format_event("error", {"message": "执行超时"})
```

---

## 注意事项

1. **浏览器兼容性**: SSE在现代浏览器中广泛支持，IE不支持
2. **连接管理**: 注意处理连接断开和重连
3. **错误处理**: 完善的错误处理机制
4. **资源消耗**: 流式连接会占用更多资源，注意控制并发数

---

## 完整示例代码

查看以下文件获取完整实现：

- 流式协调器: [core/streaming.py](../ai-service/core/streaming.py)
- API路由: [api/routes.py](../ai-service/api/routes.py)
- 演示页面: [static/index.html](../ai-service/static/index.html)
