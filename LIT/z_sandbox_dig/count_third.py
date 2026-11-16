import re
from collections import Counter

s = open(r"C:\Users\Frans PREFLM\OneDrive - University of Leeds\code\Claude\mumix\LIT\vortex-energy-balance.html", encoding="utf-8").read()
s2 = re.sub(r"data:image/[a-z]+;base64,[A-Za-z0-9+/=]+", "", s)
hs = [(m.start(), re.sub("<[^>]+>", "", m.group(2))[:45]) for m in re.finditer(r"<h([23])[^>]*>(.*?)</h\1>", s2, re.S)]


def sec(pos):
    cur = ""
    for p, t in hs:
        if p <= pos:
            cur = t
        else:
            break
    return cur


for label, lit in (("Re^(1/3)", r"Re_\lambda^{1/3}"), ("0.834", "0.834"), ("D6", "D6"), ("model I", "model I"), ("1/3", "1/3")):
    pos, c = 0, Counter()
    while True:
        i = s2.find(lit, pos)
        if i < 0:
            break
        c[sec(i)] += 1
        pos = i + 1
    print(label, sum(c.values()), dict(c))
