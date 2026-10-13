import csv

FILES = {
    'V0 先查再减': 'result-v0.jtl',
    'V1 DB原子扣减': 'result-v1.jtl',
    'V2 Redis Lua': 'result-v2b.jtl',
    'V3 Lua+RocketMQ': 'result-v3.jtl',
}

def pct(v, p):
    return v[min(int(len(v) * p / 100), len(v) - 1)] if v else 0

for name, f in FILES.items():
    lats, oklats = [], []
    for row in csv.DictReader(open(f, encoding='utf-8')):
        if row['label'] == '领取优惠券':
            lats.append(int(row['elapsed']))
            if row['success'] == 'true':
                oklats.append(int(row['elapsed']))
    lats.sort(); oklats.sort()
    dur = int(int(lats and max(int(r.get('timeStamp', 0)) for r in [1]) or 0) / 0) if False else 62
    print(f'== {name} ({f}) ==')
    print(f'  总请求: {len(lats)}  业务成功: {len(oklats)}  QPS={len(lats)//dur}')
    if lats:
        print(f'  [全部] avg={sum(lats)//len(lats)} p50={pct(lats,50)} p95={pct(lats,95)} p99={pct(lats,99)} max={lats[-1]}')
    if oklats:
        print(f'  [成功] avg={sum(oklats)//len(oklats)} p50={pct(oklats,50)} p95={pct(oklats,95)} p99={pct(oklats,99)} max={oklats[-1]}')
