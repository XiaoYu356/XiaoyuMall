import asyncio
import httpx
import json


async def test_stream_analysis():
    print("=" * 60)
    print("测试流式分析接口")
    print("=" * 60)
    
    url = "http://localhost:8000/api/v1/ai/stream/analyze"
    
    payload = {
        "product_id": "1",
        "user_id": "1",
        "user_query": "我想买一款性价比高的手机"
    }
    
    print(f"\n请求URL: {url}")
    print(f"请求数据: {json.dumps(payload, ensure_ascii=False)}\n")
    
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, json=payload, timeout=None) as response:
            print("开始接收流式数据:\n")
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        event_type = data.get("type")
                        event_data = data.get("data")
                        
                        if event_type == "start":
                            print(f"▶️  {event_data.get('message')}")
                        
                        elif event_type == "agent_start":
                            print(f"\n🤖 {event_data.get('agent')} 开始工作...")
                            print(f"   角色: {event_data.get('role')}")
                        
                        elif event_type == "agent_complete":
                            print(f"✅ {event_data.get('agent')} 完成")
                            print(f"   结果: {json.dumps(event_data.get('result'), ensure_ascii=False, indent=2)[:200]}...")
                        
                        elif event_type == "complete":
                            print(f"\n🎉 分析完成!")
                            print(f"   总耗时: {event_data.get('execution_time', 'N/A')}秒")
                            print(f"\n完整结果:")
                            print(json.dumps(event_data, ensure_ascii=False, indent=2))
                    
                    except json.JSONDecodeError:
                        print(f"解析错误: {line}")
            
            print("\n" + "=" * 60)


async def test_stream_chat():
    print("\n" + "=" * 60)
    print("测试流式对话接口")
    print("=" * 60)
    
    url = "http://localhost:8000/api/v1/ai/stream/chat"
    
    payload = {
        "product_id": "1",
        "user_id": "1",
        "user_query": "这款手机怎么样？"
    }
    
    print(f"\n请求URL: {url}")
    print(f"请求数据: {json.dumps(payload, ensure_ascii=False)}\n")
    
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, json=payload, timeout=None) as response:
            print("开始接收AI回复:\n")
            print("🤖 AI助手: ", end="", flush=True)
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        event_type = data.get("type")
                        event_data = data.get("data")
                        
                        if event_type == "llm_chunk":
                            content = event_data.get("content", "")
                            print(content, end="", flush=True)
                        
                        elif event_type == "complete":
                            print("\n\n✅ 对话完成!")
                    
                    except json.JSONDecodeError:
                        pass
            
            print("\n" + "=" * 60)


async def test_normal_analysis():
    print("\n" + "=" * 60)
    print("测试普通分析接口（非流式）")
    print("=" * 60)
    
    url = "http://localhost:8000/api/v1/ai/analyze"
    
    payload = {
        "product_id": "1",
        "user_id": "1",
        "user_query": "我想买一款性价比高的手机"
    }
    
    print(f"\n请求URL: {url}")
    print(f"请求数据: {json.dumps(payload, ensure_ascii=False)}\n")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 分析完成!")
            print(f"执行时间: {result.get('execution_time')}秒")
            print(f"参与的智能体: {', '.join(result.get('agents_involved', []))}")
            print(f"\n推荐结果:")
            recommendation = result.get("recommendation", {})
            print(f"  商品: {recommendation.get('product_name')}")
            print(f"  当前价格: ¥{recommendation.get('current_price')}")
            print(f"  最终价格: ¥{recommendation.get('final_price')}")
            print(f"  节省金额: ¥{recommendation.get('total_savings')}")
            print(f"  综合评分: {recommendation.get('overall_score')}/10")
            print(f"  购买建议: {recommendation.get('buy_recommendation')}")
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(response.text)
    
    print("\n" + "=" * 60)


async def main():
    print("\n" + "🚀 " * 30)
    print("智能购物助手 - 流式输出测试")
    print("🚀 " * 30 + "\n")
    
    print("请选择测试类型:")
    print("1. 流式分析接口")
    print("2. 流式对话接口")
    print("3. 普通分析接口（对比）")
    print("4. 全部测试")
    
    choice = input("\n请输入选项 (1-4): ").strip()
    
    if choice == "1":
        await test_stream_analysis()
    elif choice == "2":
        await test_stream_chat()
    elif choice == "3":
        await test_normal_analysis()
    elif choice == "4":
        await test_normal_analysis()
        await test_stream_analysis()
        await test_stream_chat()
    else:
        print("无效选项")


if __name__ == "__main__":
    asyncio.run(main())
