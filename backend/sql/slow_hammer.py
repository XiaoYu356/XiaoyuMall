import threading, time, requests, csv

tokens = [r['satoken'] for r in csv.DictReader(open('satokens.csv', encoding='utf-8'))]
TOKEN = tokens[0]

stop = False
count = 0

def hammer():
    global count
    s = requests.Session()
    while not stop:
        try:
            s.post('http://localhost:8083/api/v1/coupons/stats', headers={'satoken': TOKEN}, timeout=10)
        except Exception:
            pass
        count += 1

threads = [threading.Thread(target=hammer, daemon=True) for _ in range(3)]
for t in threads: t.start()
print(f'压测线程已启动, 运行35秒...')
time.sleep(35)
stop = True
time.sleep(1)
print(f'共发出 {count} 个请求')
