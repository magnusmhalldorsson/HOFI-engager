import sys, itertools, collections, glob
from flip import load, initial_height
from rounds import rounds
def popcount(x): return bin(x).count("1")

def cone_table(n, word):
    """returns k, dict: (base, T) -> list over w in 0..2k-1 of diagonal index (0..3) or None.
    Q3 C = base + span(T), base has zero bits on T.  Diagonal index = T-pattern of the class-w endpoint ... we use canonical id min(v_T, 7-v_T)."""
    N = 1 << n; k = len(word) // N; L = len(word)
    h0 = initial_height(word, n)
    P = collections.defaultdict(list)
    for i, c in enumerate(word): P[c].append(i)
    def pos(x, r):                       # position of event (x, r) in the bi-infinite periodic word
        s = (r - h0[x]) // 2; m, j = divmod(s, k)
        return P[x][j] + L * m
    table = {}
    for T in itertools.combinations(range(n), 3):
        mask = sum(1 << i for i in T)
        bits = [sum(((v >> a) & 1) << T[a] for a in range(3)) for v in range(8)]
        for base in range(N):
            if base & mask: continue
            verts = [base | bits[v] for v in range(8)]              # index v = T-pattern
            row = []
            for w in range(2 * k):
                cls = [v for v in range(8) if (popcount(verts[v]) - w) % 2 == 0]       # class of round w
                last = max(cls, key=lambda v: pos(verts[v], w))
                d = 7 - last                                                          # antipode in C
                cone = pos(verts[d], w + 1) < pos(verts[last], w)
                row.append(min(last, 7 - last) if cone else None)
            table[(base, T)] = row
    return k, table

if __name__ == "__main__":
    n = int(sys.argv[1]); files = sorted(glob.glob(sys.argv[2]))
    cnt_per_C = collections.Counter(); fac_per_win = collections.Counter(); patterns = collections.Counter()
    bad = 0; tot = 0
    for f in files:
        w = load(f); k, tab = cone_table(n, w)
        for key, row in tab.items():
            diags = {x for x in row if x is not None}
            if len(diags) < 4: bad += 1
            tot += 1
            cnt_per_C[sum(x is not None for x in row)] += 1
            # pattern up to rotation: binary cone/not cone sequence around the 2k windows
            b = tuple(int(x is not None) for x in row)
            best = min(b[i:] + b[:i] for i in range(len(b)))
            patterns[best] += 1
        # per window: how many Q3's are cones simultaneously (as a fraction)
        for wnd in range(2 * k):
            fac_per_win[round(sum(1 for r in tab.values() if r[wnd] is not None) / len(tab), 3)] += 1
    print(f"n={n}: {len(files)} solutions, {tot} (solution,Q3) samples; Q3s missing a diagonal: {bad} (must be 0)")
    print("  #cone windows per Q3 (of %d):" % (2 * k), dict(sorted(cnt_per_C.items())))
    print("  most common cone/non-cone cyclic patterns (1=cone window):")
    for p, c in patterns.most_common(6): print("    ", "".join(map(str, p)), c)
    fr = sorted(fac_per_win.items())
    print("  fraction of Q3s that are cones in one window: min %.3f max %.3f" % (fr[0][0], fr[-1][0]))
