"""
多进程压测工具: 排除Python GIL干扰, 测服务器真实并发能力
用法: python mp_hammer.py <url> [进程数] [每进程线程数] [持续秒数]
"""
import sys
import time
import threading
import multiprocessing as mp

def worker(url, token, duration, nthread, out):
    import requests as rq
    stop = time.time() + duration
    lats = []
    errbodies = []
    local = threading.local()
    def run():
        if not hasattr(local, 's'):
            local.s = rq.Session()
        while time.time() < stop:
            t = time.perf_counter()
            try:
                r = local.s.post(url, headers={'satoken': token}, timeout=15)
                body = r.text[:400]
                if r.status_code != 200 or '"code":200' not in body:
                    errbodies.append(f'[{r.status_code}] {body}')
            except Exception as e:
                errbodies.append(f'[EXC] {str(e)[:200]}')
            lats.append((time.perf_counter() - t) * 1000)
    threads = [threading.Thread(target=run) for _ in range(nthread)]
    for th in threads: th.start()
    for th in threads: th.join()
    out.put((lats, errbodies))

def main():
    url = sys.argv[1]
    nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    nthread = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    duration = int(sys.argv[4]) if len(sys.argv) > 4 else 10

    import csv
    from pathlib import Path
    token = next(csv.DictReader(open(Path(__file__).parent / 'satokens.csv', encoding='utf-8')))['satoken']

    print(f'目标: {url}')
    print(f'{nproc}进程 x {nthread}线程 = {nproc*nthread}并发, 持续{duration}s')
    out = mp.Queue()
    procs = [mp.Process(target=worker, args=(url, token, duration, nthread, out)) for _ in range(nproc)]
    t0 = time.time()
    for p in procs: p.start()
    all_lats, all_errs = [], []
    for _ in range(nproc):
        lats, errs = out.get()
        all_lats.extend(lats)
        all_errs.extend(errs)
    for p in procs: p.join()
    elapsed = time.time() - t0

    all_lats.sort()
    n = len(all_lats)
    def pct(p): return all_lats[min(int(n * p / 100), n - 1)]
    print(f'请求={n} QPS={n/elapsed:.0f} p50={pct(50):.0f}ms p95={pct(95):.0f}ms p99={pct(99):.0f}ms avg={sum(all_lats)/n:.0f}ms')
    print(f'异常响应={len(all_errs)}个')
    from collections import Counter
    for body, c in Counter(all_errs).most_common(3):
        print(f'  [{c}次] {body[:300]}')

if __name__ == '__main__':
    mp.freeze_support()
    main()
