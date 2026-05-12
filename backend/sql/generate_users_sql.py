import os

BCRYPT_HASH = "$2a$10$nUOkzR2hPe9l40vBfHwn.ehMWvN1i1oyWFX8KDSD2q2fb5dVhuruW"
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "insert_1000_users.sql")

lines = []
lines.append("USE mall_user;")
lines.append("")
lines.append("-- 1000个测试用户，密码均为 123456 (BCrypt加密)")
lines.append("-- BCrypt hash: $2a$10$nUOkzR2hPe9l40vBfHwn.ehMWvN1i1oyWFX8KDSD2q2fb5dVhuruW")
lines.append("-- 手机号范围: 13800101001 ~ 13800102000")
lines.append("-- 用户名范围: user_1001 ~ user_2000")
lines.append("")
lines.append("INSERT IGNORE INTO `user` (`id`, `username`, `password`, `nickname`, `phone`, `email`, `gender`, `status`, `level`) VALUES")

values = []
for i in range(1000):
    user_id = 1001 + i
    username = f"user_{user_id}"
    nickname = f"用户{user_id}"
    phone = f"1380010{i + 1001:04d}"
    email = f"user{user_id}@test.com"
    gender = 1 if i % 2 == 0 else 2
    values.append(f"({user_id}, '{username}', '{BCRYPT_HASH}', '{nickname}', '{phone}', '{email}', {gender}, 1, 1)")

lines.append(",\n".join(values) + ";")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"SQL文件已生成: {OUTPUT_FILE}")
print(f"共生成 {len(values)} 条用户数据")
