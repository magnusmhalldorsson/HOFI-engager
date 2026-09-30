import sys, collections
from flip import load, initial_height
def popcount(x): return bin(x).count("1")

def rounds(n, word):
    """alpha[r] for r in 0..2k-1 : vertices of parity r%2 in the order of their rank-r events (rank = height before firing, mod 2k)."""
    N = 1 << n; k = len(word) // N; L = len(word)
    h0 = initial_height(word, n)
    P = collections.defaultdict(list)
    for i, c in enumerate(word): P[c].append(i)
    alpha = {}
    # event (x, r): r = h0(x) + 2s, s = j + k*m ; position = P[x][j] + L*m
    for r in range(2 * k):
        ev = []
        for x in range(N):
            if (popcount(x) - r) % 2: continue
            s = (r - h0[x]) // 2
            m, j = divmod(s, k)
            ev.append((P[x][j] + L * m, x))
        ev.sort()
        alpha[r] = [x for _, x in ev]
    return k, alpha

def spearman(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    sxx = sum((a - mx) ** 2 for a in xs); syy = sum((b - my) ** 2 for b in ys)
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    return sxy / (sxx * syy) ** 0.5 if sxx and syy else 0.0

if __name__ == "__main__":
    n = int(sys.argv[1]); w = load(sys.argv[2]); N = 1 << n
    k, alpha = rounds(n, w)
    print(f"n={n} k={k}: {2*k} rounds, each a permutation of {N//2} vertices")
    for r in range(2 * k):
        order = alpha[r]; pos = {x: i for i, x in enumerate(order)}
        best = (-2, None)
        for u in range(N):
            cls = [x for x in order]
            c = spearman([pos[x] for x in cls], [popcount(x ^ u) for x in cls])
            if c > best[0]: best = (c, u)
        print(f"  round {r}: best 'center' u={best[1]:0{n}b}  Spearman(position, dist to u) = {best[0]:.3f}")
