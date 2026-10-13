import pymysql

conn = pymysql.connect(host='localhost', user='root', password='root', database='mall_coupon')
cur = conn.cursor()
cur.execute("SHOW VARIABLES LIKE 'max_connections'")
print('max_connections:', cur.fetchone())
cur.execute("SHOW STATUS LIKE 'Threads_connected'")
print('Threads_connected:', cur.fetchone())
cur.execute("SELECT id, user, db, command, time, state, LEFT(info,80) FROM information_schema.processlist ORDER BY time DESC LIMIT 15")
print()
print(f"{'id':>6} {'user':<12} {'db':<16} {'command':<10} {'time':>5} {'state':<22} info")
for row in cur.fetchall():
    print(f"{row[0]:>6} {str(row[1]):<12} {str(row[2]):<16} {str(row[3]):<10} {row[4]:>5} {str(row[5]):<22} {row[6]}")
cur.execute("SELECT COUNT(*) FROM information_schema.processlist")
print('\n进程总数:', cur.fetchone()[0])
