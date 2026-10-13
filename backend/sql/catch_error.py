"""小并发抓真实错误响应体"""
import csv, time, threading, requests

tokens = [r['satoken'] for r in csv.DictReader(open('satokens.csv', encoding='utf-8'))]
TOKEN = tokens[0]
errs = []
lock = threading.Lock()

def one(i):
    try:
        r = requests.post('http://localhost:8080/api/v1/coupons/stats', headers={'satoken': TOKEN}, timeout=15)
        if r.status_code != 200:
            with lock:
                errs.append((r.status_code, r.text[:600]))
    except Exception as e:
        with lock:
            errs.append(('EXC', str(e)[:300]))

ts = []
for _ in range(3):
    ts = [threading.Thread(target=one, args=(i,)) for i in range(200)]
    t0 = time.time()
    for t in ts: t.start()
    for t in ts: t.join()

print(f'完成, 捕获错误 {len(errs)} 个')
for code, body in errs[:3]:
    print(f'--- [{code}] ---')
    print(body)
