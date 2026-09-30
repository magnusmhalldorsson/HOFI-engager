import sys
n, k = int(sys.argv[1]), int(sys.argv[2]); cnf, model = sys.argv[3], sys.argv[4]
N = 1 << n; occ = [(v, j) for v in range(N) for j in range(k)]; M = len(occ)
# variable numbering replicates direct_cnf.lit: (i,j) i<j first-come numbering -> rebuild by replaying
var = {}
import itertools
def lit_var(i, j):
    return var.setdefault((i, j), len(var) + 1)
# replay in the same order as the generator: same-letter copies first, then transitivity loops
idx = {o: i for i, o in enumerate(occ)}
def reg(p, q):
    i, j = idx[p], idx[q]
    lit_var(min(i, j), max(i, j))
for v in range(N):
    for j in range(k - 1): reg((v, j), (v, j + 1))
for a in range(M):
    for b in range(M):
        if a == b: continue
        for c in range(M):
            if c == a or c == b: continue
            reg(occ[a], occ[b]); reg(occ[b], occ[c]); reg(occ[a], occ[c])
true = set()
for line in open(model):
    if line.startswith("v"):
        for t in line.split()[1:]:
            t = int(t)
            if t > 0: true.add(t)
# position of occurrence = number of occurrences that precede it
before = [0] * M
for (i, j), vid in var.items():
    if vid in true: before[j] += 1          # i before j
    else: before[i] += 1                    # j before i
order = sorted(range(M), key=lambda i: before[i])
print(" ".join(str(occ[i][0]) for i in order))
