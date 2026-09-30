"""Theory-free CNF: does Q_n have a k-uniform word representant?  Straight from the definition.
Variables: a linear order on the k*2^n occurrences (occurrence (v,j) = j-th copy of letter v, copies of a letter
kept in order WLOG).  Letters x,y alternate iff x_0<y_0<x_1<y_1<...<x_{k-1}<y_{k-1} or the same with x,y swapped.
WLOG (cyclic shift, Kitaev-Pyatkin) the word starts with an occurrence of letter 0.
Usage: direct_cnf.py n k out.cnf
"""
import sys, itertools
n, k, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
N = 1 << n
occ = [(v, j) for v in range(N) for j in range(k)]
idx = {o: i for i, o in enumerate(occ)}
M = len(occ)
var = {}
def lit(p, q):                       # literal for "occurrence p before occurrence q"
    i, j = idx[p], idx[q]
    if i < j:
        return var.setdefault((i, j), len(var) + 1)
    return -var.setdefault((j, i), len(var) + 1)
clauses = []
# same-letter copies in order
for v in range(N):
    for j in range(k - 1):
        clauses.append([lit((v, j), (v, j + 1))])
# transitivity
for a, b, c in itertools.permutations(range(M), 3):
    if a < b and a < c or True:
        pass
ids = range(M)
for a in ids:
    for b in ids:
        if a == b: continue
        for c in ids:
            if c == a or c == b: continue
            clauses.append([-lit(occ[a], occ[b]), -lit(occ[b], occ[c]), lit(occ[a], occ[c])])
# first letter is 0: occurrence (0,0) precedes everything else
for o in occ:
    if o != (0, 0):
        clauses.append([lit((0, 0), o)])
nv = len(var)
def chain(x, y):                     # x first: x0<y0<x1<y1<...
    L = []
    for j in range(k):
        L.append(lit((x, j), (y, j)))
        if j + 1 < k: L.append(lit((y, j), (x, j + 1)))
    return L
for x in range(N):
    for y in range(x + 1, N):
        A, B = chain(x, y), chain(y, x)
        if bin(x ^ y).count("1") == 1:               # edge: A or B
            nv += 1; s = nv
            for l in A: clauses.append([-s, l])
            for l in B: clauses.append([s, l])
        else:                                        # non-edge: neither
            clauses.append([-l for l in A])
            clauses.append([-l for l in B])
with open(out, "w") as f:
    f.write(f"p cnf {nv} {len(clauses)}\n")
    for c in clauses: f.write(" ".join(map(str, c)) + " 0\n")
print(f"Q_{n}, k={k}: {M} occurrences, {nv} vars, {len(clauses)} clauses")
