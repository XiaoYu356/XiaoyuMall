import csv, pymysql
import redis as redislib

conn = pymysql.connect(host='localhost', user='root', password='root', database='mall_coupon')
cur = conn.cursor()
cur.execute("SELECT used_count, total_count FROM coupon_template WHERE id=25")
print('券25 DB状态(used,total):', cur.fetchone())
cur.execute("SELECT COUNT(1) FROM user_coupon WHERE template_id=25")
print('券25 实际领取条数:', cur.fetchone()[0])
cur.execute("SELECT COUNT(DISTINCT user_id) FROM user_coupon WHERE template_id=25")
print('去重用户数:', cur.fetchone()[0])

lats, oklats = [], []
for row in csv.DictReader(open('result-v2b.jtl', encoding='utf-8')):
    if row['label'] == '领取优惠券':
        lats.append(int(row['elapsed']))
        if row['success'] == 'true':
            oklats.append(int(row['elapsed']))
lats.sort(); oklats.sort()
def pct(v, p):
    return v[min(int(len(v) * p / 100), len(v) - 1)]
print(f'业务成功数: {len(oklats)} (预期100)')
print(f'[全部] QPS=90289/62s=1456 avg={sum(lats)//len(lats)}ms p50={pct(lats,50)}ms p95={pct(lats,95)}ms p99={pct(lats,99)}ms')
if oklats:
    print(f'[成功] avg={sum(oklats)//len(oklats)}ms p50={pct(oklats,50)}ms p95={pct(oklats,95)}ms p99={pct(oklats,99)}ms')

r = redislib.Redis(host='localhost', port=6379, db=0)
print('Redis剩余库存:', r.get('coupon:stock:25'), '已领用户set数:', r.scard('coupon:received:25'))
