import re

content = open('jstack_load.txt', encoding='utf-8', errors='replace').read()
blocks = re.split(r'\n"', '\n' + content)
shown = 0
for b in blocks:
    name = b.split('"')[0] if b.startswith('"') else b.split(' ')[0]
    if 'exec' not in name or 'handleException' not in b:
        continue
    print('线程:', name)
    print(b[:1600])
    print('=' * 80)
    shown += 1
    if shown >= 2:
        break
