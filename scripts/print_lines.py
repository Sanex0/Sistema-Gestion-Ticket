import sys
p='flask_app/models/mensaje_model.py'
with open(p, 'r', encoding='utf-8') as f:
    lines=f.read().splitlines()
start=360
end=400
for i in range(start, end+1):
    if i-1 < len(lines):
        print(f"{i:4d}: {lines[i-1]}")
