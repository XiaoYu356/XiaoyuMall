import requests
import csv
import time
import concurrent.futures
from threading import Lock

BASE_URL = "http://localhost:8080"
LOGIN_URL = f"{BASE_URL}/api/v1/users/login"
PASSWORD = "123456"
OUTPUT_CSV = "satokens.csv"
USER_START = 1001
USER_END = 2000
MAX_WORKERS = 20
BATCH_SIZE = 50
BATCH_DELAY = 2

write_lock = Lock()
success_count = 0
fail_count = 0


def login_user(user_id):
    phone = f"1380010{user_id:04d}"
    payload = {"phone": phone, "password": PASSWORD}
    global success_count, fail_count
    try:
        resp = requests.post(LOGIN_URL, json=payload, timeout=10)
        data = resp.json()
        if data.get("code") == 200 and data.get("data"):
            token = data["data"]
            with write_lock:
                success_count += 1
            return {"user_id": user_id, "satoken": token, "ok": True}
        else:
            msg = data.get("message", "unknown error")
            with write_lock:
                fail_count += 1
            return {"user_id": user_id, "satoken": "", "ok": False, "msg": msg}
    except Exception as e:
        with write_lock:
            fail_count += 1
        return {"user_id": user_id, "satoken": "", "ok": False, "msg": str(e)}


def main():
    global success_count, fail_count
    start_time = time.time()

    all_results = []
    user_ids = list(range(USER_START, USER_END + 1))
    total = len(user_ids)
    batch_count = (total + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"开始登录 {total} 个用户...")
    print(f"登录接口: {LOGIN_URL}")
    print(f"并发线程数: {MAX_WORKERS}")
    print(f"每批数量: {BATCH_SIZE}, 共 {batch_count} 批, 批间间隔: {BATCH_DELAY}秒")
    print(f"输出文件: {OUTPUT_CSV}")
    print("-" * 60)

    for i in range(batch_count):
        batch_start = i * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, total)
        batch_ids = user_ids[batch_start:batch_end]
        batch_num = i + 1

        print(f"\n[批次 {batch_num}/{batch_count}] 登录用户 {batch_ids[0]}-{batch_ids[-1]} ({len(batch_ids)}人)")

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_uid = {executor.submit(login_user, uid): uid for uid in batch_ids}
            for future in concurrent.futures.as_completed(future_to_uid):
                result = future.result()
                all_results.append(result)
                if result["ok"]:
                    print(f"  [OK] user_id={result['user_id']} token={result['satoken'][:16]}...")
                else:
                    print(f"  [FAIL] user_id={result['user_id']} {result['msg']}")

        if i < batch_count - 1:
            print(f"  等待 {BATCH_DELAY} 秒后继续下一批...")
            time.sleep(BATCH_DELAY)

    all_results.sort(key=lambda x: x["user_id"])

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["satoken"])
        for r in all_results:
            if r["ok"]:
                writer.writerow([r["satoken"]])

    elapsed = time.time() - start_time
    print("-" * 60)
    print(f"完成! 耗时: {elapsed:.2f}秒")
    print(f"成功: {success_count}, 失败: {fail_count}")
    print(f"结果已保存到: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
