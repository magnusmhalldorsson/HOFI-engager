"""Exact WR(n,k) checker in the permutation model.
A system is 2k permutations alpha[r] (r in Z_{2k}) of the vertices of parity r%2.  Window r interleaves alpha[r] (rank r) with
alpha[r+1] (rank r+1) by the earliest placement: b (rank r+1) is placed right after the last neighbour, and after the previous b.
Inversion (b before a) iff pos_r(a) > t_r(b), t_r(b) = prefix-max over alpha[r+1] up to b of the last-neighbour position.
Conditions (exactly WR(n,k)): every distance-2 pair is ordered both ways among the k rounds of its class;
every distance-3 pair is inverted in some window (either direction).
"""
import itertools

def popcount(x): return bin(x).count("1")

class WR:
    def __init__(self, n, k):
        self.n, self.k, self.N = n, k, 1 << n
        N = self.N
        self.d3 = [[y ^ sum(1 << i for i in T) for T in itertools.combinations(range(n), 3)] for y in range(N)]
        self.nb = [[y ^ (1 << i) for i in range(n)] for y in range(N)]
        self.d2 = [[y ^ (1 << i) ^ (1 << j) for i, j in itertools.combinations(range(n), 2)] for y in range(N)]
        self.cls = [[v for v in range(N) if popcount(v) % 2 == p] for p in (0, 1)]

    def evaluate(self, alphas, detail=False):
        n, k, N = self.n, self.k, self.N
        pos = []
        for a in alphas:
            p = [0] * N
            for i, v in enumerate(a): p[v] = i
            pos.append(p)
        # d=2 coverage: pair (x<z) needs both orders among rounds of its class
        unc2 = 0
        for par in (0, 1):
            rounds = [pos[r] for r in range(2 * k) if r % 2 == par]
            for x in self.cls[par]:
                for z in self.d2[x]:
                    if z > x:
                        s = sum(1 for p in rounds if p[x] < p[z])
                        if s == 0 or s == len(rounds): unc2 += 1
        # d=3 coverage
        covered = set()
        for r in range(2 * k):
            A = alphas[r]; B = alphas[(r + 1) % (2 * k)]
            pa = pos[r]; t = -1
            for b in B:
                m = max(pa[a] for a in self.nb[b])
                if m > t: t = m
                for a in self.d3[b]:
                    if pa[a] > t:
                        covered.add((a, b) if a < b else (b, a))
        total3 = N * (n * (n - 1) * (n - 2) // 6) // 2
        unc3 = total3 - len(covered)
        return (unc2, unc3) if detail else unc2 + unc3
