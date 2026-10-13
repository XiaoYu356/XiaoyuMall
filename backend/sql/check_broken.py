import csv, requests, time
import pymysql

tokens = [r['satoken'] for r in csv.DictReader(open('satokens.csv', encoding='utf-8'))]
TOKEN = tokens[0]

for url, label in [('http://localhost:8083/api/v1/coupons/stats', '直连coupon'),
                   ('http://localhost:8080/api/v1/coupons/stats', '走网关')]:
    t = time.perf_counter()
    try:
        r = requests.post(url, headers={'satoken': TOKEN}, timeout=20).json()
        print(f'{label}: code={r["code"]} {r["message"]}  耗时{(time.perf_counter()-t)*1000:.0f}ms')
    except Exception as e:
        print(f'{label}: 客户端异常 {str(e)[:80]}  耗时{(time.perf_counter()-t)*1000:.0f}ms')

conn = pymysql.connect(host='localhost', user='root', password='root', database='mall_coupon')
cur = conn.cursor()
cur.execute("SELECT IFNULL(db,'NULL'), COUNT(*) FROM information_schema.processlist GROUP BY db")
print('MySQL连接按库分布:', dict(cur.fetchall()))
