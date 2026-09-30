import sys, itertools, collections
from flip import load, simulate
def popcount(x): return bin(x).count("1")

def run(n, word):
    N = 1 << n; k = len(word) // N
    stats = collections.Counter(); rows = []
    tri_all = list(itertools.combinations(range(n), 3))
    def rec(t, x, h):
        hx = h[x]
        G = {}
        for i, j in itertools.combinations(range(n), 2):
            G[(i, j)] = (h[x ^ (1 << i) ^ (1 << j)] - hx) == 2      # lambda = 2  <=> edge of G
        cone = anti = tri = atri = 0
        for (i, j, l) in tri_all:
            y = x ^ (1 << i) ^ (1 << j) ^ (1 << l); lam = h[y] - hx
            eij, eil, ejl = G[(i, j)], G[(i, l)], G[(j, l)]
            if eij and eil and ejl:
                tri += 1
                if lam == 3: cone += 1
            if (not eij) and (not eil) and (not ejl):
                atri += 1
                if lam == -1: anti += 1
            # consistency: lambda=3 only from a G-triangle, lambda=-1 only from an independent triple
            if lam == 3: assert eij and eil and ejl
            if lam == -1: assert (not eij) and (not eil) and (not ejl)
        e = sum(G.values())
        rows.append((e, tri, cone, atri, anti))
    simulate(word, n, rec)
    return k, rows

if __name__ == "__main__":
    n = int(sys.argv[1]); w = load(sys.argv[2])
    k, rows = run(n, w)
    F = len(rows); C3 = n * (n - 1) * (n - 2) // 6
    avg = lambda idx: sum(r[idx] for r in rows) / F
    print(f"n={n} k={k} firings={F}  C(n,3)={C3}")
    print(f"  avg edges of G            = {avg(0):.3f}   (exact prediction C(n,2)/2 = {n*(n-1)/4:.3f})")
    print(f"  avg triangles of G        = {avg(1):.3f}   avg cones     = {avg(2):.3f}")
    print(f"  avg indep. triples of G   = {avg(3):.3f}   avg anticones = {avg(4):.3f}")
    print(f"  needed (cones) per firing >= C(n,3)/(2k) = {C3/(2*k):.3f}; random G(n,1/2) triangles = {C3/8:.3f}")
    print(f"  fraction of G-triangles that are cones = {sum(r[2] for r in rows)/max(1,sum(r[1] for r in rows)):.3f};"
          f" of independent triples that are anticones = {sum(r[4] for r in rows)/max(1,sum(r[3] for r in rows)):.3f}")
    eds = collections.Counter(r[0] for r in rows)
    print("  distribution of #edges of G:", dict(sorted(eds.items())))
