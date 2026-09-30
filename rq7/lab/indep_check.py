import sys, random
w = list(map(int, open(sys.argv[1]).read().split())); n = int(sys.argv[2]); N = 1 << n
assert all(0 <= c < N for c in w)
pos = {v: [] for v in range(N)}
for i, c in enumerate(w): pos[c].append(i)
k = len(pos[0]); assert all(len(p) == k for p in pos.values()) and len(w) == k * N, "not uniform"

def alt_linear(x, y):
    # subword on {x,y} read left to right must have no two equal adjacent letters
    sub = [c for c in w if c == x or c == y]
    return all(sub[i] != sub[i + 1] for i in range(len(sub) - 1))

def run(word_pos_check=True):
    edges = nonedge_alt = edge_nonalt = 0
    for x in range(N):
        for y in range(x + 1, N):
            a = alt_linear(x, y)
            adj = bin(x ^ y).count("1") == 1
            edges += adj
            if adj and not a: edge_nonalt += 1
            if (not adj) and a: nonedge_alt += 1
    return edges, edge_nonalt, nonedge_alt

e, en, ne = run()
print(f"n={n} k={k} len={len(w)} edges={e} (expect {n * (N // 2)}) edges-not-alternating={en} nonedges-alternating={ne}")
sys.exit(0 if (en == 0 and ne == 0 and e == n * (N // 2)) else 1)
