"""
优惠券秒杀压测脚本(命令行版)
用法: python stress_receive.py <templateId> [并发数]
示例: python stress_receive.py 5 200

流程:
1. 预热: 用轻量查询接口走通 网关->coupon-service->MySQL 链路
   (预热JIT/连接池/Tomcat线程池; 不能用领券接口预热, 会消耗每人一次的领取资格), 不计入统计
2. 正式压测: 读取同目录 satokens.csv, 每个 token 发一次领取请求,
   start_event 同步放行, 模拟秒杀瞬时洪峰
3. 统计: 全部请求与成功请求分别输出 QPS、avg/p50/p95/p99/max 延迟
   (秒杀下大量"已领完"快速失败会拉低均值, 成功请求RT须单独看)
"""
import csv
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

BASE_URL = "http://localhost:8080"
TOKENS_FILE = Path(__file__).parent / "satokens.csv"
WARMUP_REQUESTS = 30  # 预热请求数


def load_tokens():
    with open(TOKENS_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row["satoken"] for row in reader if row.get("satoken")]


def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0
    idx = min(int(len(sorted_vals) * p / 100), len(sorted_vals) - 1)
    return sorted_vals[idx]


def warmup(token):
    """用领券中心查询接口预热完整链路, 不消耗领券资格; 返回链路是否可达"""
    url = f"{BASE_URL}/api/v1/coupons/available"
    ok_count = 0

    def one(_):
        nonlocal ok_count
        try:
            resp = requests.get(
                url, headers={"satoken": token},
                params={"pageNum": 1, "pageSize": 1}, timeout=15)
            if resp.status_code == 200:
                ok_count += 1
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=10) as pool:
        list(pool.map(one, range(WARMUP_REQUESTS)))
    return ok_count > 0


def main():
    if len(sys.argv) < 2:
        print("用法: python stress_receive.py <templateId> [并发数]")
        sys.exit(1)
    template_id = sys.argv[1]
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 200

    tokens = load_tokens()
    total = len(tokens)
    if not tokens:
        print("satokens.csv 为空, 请先运行 get_satokens.py 生成 token")
        sys.exit(1)

    # ---------- 预热(不计入统计) ----------
    print(f"[预热] {WARMUP_REQUESTS} 次查询请求, 预热JIT/连接池, 不消耗领券资格...")
    if not warmup(tokens[0]):
        print("预热失败: 服务不可达, 请检查网关和coupon-service是否启动")
        sys.exit(1)
    time.sleep(1)  # 让预热连接归位
    print("[预热] 完成")
    print("-" * 60)

    print(f"压测目标: POST {BASE_URL}/api/v1/coupons/receive/{template_id}")
    print(f"请求数: {total}, 并发数: {concurrency}")
    print("-" * 60)

    results = []
    lock = threading.Lock()
    start_event = threading.Event()
    session_local = threading.local()

    def worker(idx):
        if not hasattr(session_local, "s"):
            session_local.s = requests.Session()
        token = tokens[idx]
        start_event.wait()
        start = time.perf_counter()
        try:
            resp = session_local.s.post(
                f"{BASE_URL}/api/v1/coupons/receive/{template_id}",
                headers={"satoken": token},
                timeout=15,
            )
            elapsed = (time.perf_counter() - start) * 1000
            try:
                data = resp.json()
                ok = data.get("code") == 200
                msg = data.get("message", "")
            except ValueError:
                ok, msg = False, f"HTTP{resp.status_code}: {resp.text[:80]}"
            with lock:
                results.append((ok, elapsed, msg))
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            with lock:
                results.append((False, elapsed, f"EXC: {e}"))

    pool = threading.ThreadPoolExecutor(max_workers=concurrency)
    futures = [pool.submit(worker, i) for i in range(total)]
    time.sleep(0.5)  # 等待线程池把首批 worker 拉起并阻塞在 start_event 上
    start_time = time.perf_counter()
    start_event.set()
    pool.shutdown(wait=True)
    elapsed_total = time.perf_counter() - start_time

    # ---------- 统计 ----------
    msg_counter = {}
    for ok, _, msg in results:
        key = ("成功" if ok else "失败") + " | " + (msg or "-")
        msg_counter[key] = msg_counter.get(key, 0) + 1

    all_lat = sorted(r[1] for r in results)
    ok_lat = sorted(r[1] for r in results if r[0])

    def report(name, lats):
        if not lats:
            return
        print(
            f"[{name}] QPS={len(lats) / elapsed_total:.1f} "
            f"avg={sum(lats) / len(lats):.0f}ms "
            f"p50={percentile(lats, 50):.0f}ms "
            f"p95={percentile(lats, 95):.0f}ms "
            f"p99={percentile(lats, 99):.0f}ms "
            f"max={lats[-1]:.0f}ms"
        )

    print("-" * 60)
    print(f"总耗时: {elapsed_total:.2f}s")
    for key, cnt in sorted(msg_counter.items(), key=lambda x: -x[1]):
        print(f"  {key}: {cnt}")
    report("全部请求", all_lat)
    report("成功领取", ok_lat)
    print("-" * 60)
    print("结果核验SQL:")
    print(f"  SELECT COUNT(*) FROM mall_coupon.user_coupon WHERE template_id={template_id};")
    print(f"  SELECT total_count, used_count FROM mall_coupon.coupon_template WHERE id={template_id};")


if __name__ == "__main__":
    main()
