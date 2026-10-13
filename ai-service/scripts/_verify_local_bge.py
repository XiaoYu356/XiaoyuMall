"""快速验证本地 bge-m3 embedding + bge-reranker-v2-m3 能跑通。

cwd=ai-service，执行：.venv\\Scripts\\python.exe -m scripts._verify_local_bge
"""
import asyncio
import sys
sys.path.insert(0, ".")

from app.core.embeddings import embed_text
from app.core.reranker import rerank, build_rerank_doc


async def main():
    print("=== 验证本地 bge-m3 embedding ===")
    vec = await embed_text("7天无理由退货条件")
    print(f"  维度: {len(vec)} (期望 1024)")
    print(f"  前5维: {vec[:5]}")

    print("\n=== 验证本地 bge-reranker-v2-m3 ===")
    query = "退款多久到账"
    docs = [
        {"question": "退款到账时效", "answer": "原路退回3-7个工作日"},
        {"question": "退货流程说明", "answer": "申请退货→寄回→质检→退款"},
        {"question": "优惠券使用规则", "answer": "满减券不叠加"},
    ]
    ranked = await rerank(query, [build_rerank_doc(d) for d in docs], top_n=3)
    print(f"  排序结果: {[(docs[i]['question'], round(s, 4)) for i, s in ranked]}")
    print(f"  第一条分数 {ranked[0][1]:.4f} > 第二条 {ranked[1][1]:.4f}？{ranked[0][1] > ranked[1][1]}")

    print("\n✅ 本地模型验证通过")


asyncio.run(main())
