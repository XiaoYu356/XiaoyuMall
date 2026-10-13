import re
from collections import Counter

content = open('jstack_load.txt', encoding='utf-8', errors='replace').read()
blocks = re.split(r'\n"', '\n' + content)

states, tops = Counter(), Counter()
for b in blocks:
    name = b.split('"')[0] if b.startswith('"') else b.split(' ')[0]
    if 'exec' not in name and 'http-nio' not in name:
        continue
    m = re.search(r'java.lang.Thread.State: (\S+)', b)
    st = m.group(1) if m else '?'
    states[st] += 1
    frames = [l.strip() for l in b.split('\n') if re.match(r'\s+at ', l)]
    for f in frames:
        if any(k in f for k in ['mall', 'druid', 'lettuce', 'redis', 'satoken', 'tomcat', 'mybatis', 'mysql']):
            tops[(st, f.split('(')[0][:110])] += 1
            break

print('=== Tomcat线程状态分布 ===')
for s, c in states.most_common():
    print(f'{s}: {c}')
print()
print('=== 线程卡住的位置TOP15 ===')
for (s, f), c in tops.most_common(15):
    print(f'[{c:3d}个] {s[:8]:8s} {f}')
