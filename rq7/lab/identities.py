import sys, collections
from flip import load, simulate

def popcount(x): return bin(x).count("1")

def analyse(n, word):
    N = 1 << n; k = len(word) // N
    lam = collections.defaultdict(list)            # unordered pair -> list of lambda at each of its 2k firings
    def rec(t, x, h):
        hx = h[x]
        for y in range(N):
            if y != x:
                lam[(x, y) if x < y else (y, x)].append(h[y] - hx)
    simulate(word, n, rec)
    bad = []
    by_d = collections.defaultdict(lambda: collections.Counter())
    for (x, y), L in lam.items():
        d = popcount(x ^ y)
        assert len(L) == 2 * k
        if sum(L) != 2 * k: bad.append(("sum", x, y, d, sum(L)))
        for v in L: by_d[d][v] += 1
        if d == 2 and sum(1 for v in L if v == 2) != k: bad.append(("d2split", x, y))
        if d == 3 and L.count(3) != L.count(-1): bad.append(("d3balance", x, y, L.count(3), L.count(-1)))
    return k, by_d, bad

if __name__ == "__main__":
    n = int(sys.argv[1]); w = load(sys.argv[2])
    k, by_d, bad = analyse(n, w)
    print(f"n={n} k={k}: violations of the exact identities: {len(bad)}")
    for d in sorted(by_d):
        tot = sum(by_d[d].values()); mean = sum(v * c for v, c in by_d[d].items()) / tot
        dist = {v: c for v, c in sorted(by_d[d].items())}
        print(f"  distance {d}: mean lambda = {mean:.4f}; values {dist}")
