#!/usr/bin/env python3
"""
PFR+(n, k): orders of same-rank events at distance 2 only (as PFR), with the exact Q_3
extremality condition in place of PFR's (C) and (D):
 (tri) transitivity on the stars N(y) (every triangle of the halved cube lies in a star);
 (E)   a distance-2 pair is not ordered the same way in all k rounds of its parity;
 (QX)  for every Q_3 C and every diagonal {x, x'} of C (x of parity r, x' of parity r+1):
       some window w with an inversion on this diagonal, i.e.
         w = r (mod 2):   x last among C's parity-r vertices in round w and
                          x' first among C's parity-(r+1) vertices in round w+1, or
         w = r+1 (mod 2): x' last among C's parity-(r+1) vertices in round w and
                          x first among C's parity-r vertices in round w+1.
       (An inversion (d, w+1) < (c, w) on the diagonal {c, d} forces every C-neighbour of d,
       i.e. every other parity-w vertex of C, before (d, w+1) < (c, w), and every C-neighbour
       of c after (c, w) > (d, w+1).)
Symmetry: (0,0) follows its distance-2 vertices in round 0; the neighbours of 0 are in order
in round 1.
"""
import itertools, sys


def popcount(x):
    return bin(x).count("1")


class PFRP:
    def __init__(self, n, k, subset=None):
        self.n, self.k, self.P, self.N = n, k, 2 * k, 1 << n
        self.var, self.clauses = {}, []
        self.S = set(range(self.N)) if subset is None else set(subset)

    def v(self, key):
        if key not in self.var:
            self.var[key] = len(self.var) + 1
        return self.var[key]

    def o(self, s, a, b):
        s %= self.P
        assert popcount(a ^ b) == 2 and popcount(a) % 2 == s % 2
        return self.v(("o", s, a, b)) if a < b else -self.v(("o", s, b, a))

    def new(self):
        return self.v(("aux", len(self.var)))

    def build(self, sym=True):
        n, P, N, S = self.n, self.P, self.N, self.S
        add = self.clauses.append
        for s in range(P):
            for y in range(N):
                if popcount(y) % 2 == s % 2:
                    continue
                nb = [y ^ (1 << i) for i in range(n) if y ^ (1 << i) in S]
                for a, b, c in itertools.permutations(nb, 3):
                    add([-self.o(s, a, b), -self.o(s, b, c), self.o(s, a, c)])
        for a in S:
            for i, j in itertools.combinations(range(n), 2):
                b = a ^ (1 << i) ^ (1 << j)
                if a > b or b not in S:
                    continue
                rs = [s for s in range(P) if s % 2 == popcount(a) % 2]
                add([self.o(s, a, b) for s in rs])
                add([-self.o(s, a, b) for s in rs])
        for base in range(N):
            for T in itertools.combinations(range(n), 3):
                if any(base >> t & 1 for t in T):
                    continue
                C = [base ^ sum(1 << T[q] for q in range(3) if m >> q & 1) for m in range(8)]
                if not set(C) <= S:
                    continue
                full = sum(1 << t for t in T)
                for x in C:
                    if popcount(x) % 2:
                        continue                      # each diagonal once: x even
                    xb = x ^ full
                    ors = []
                    for w in range(P):
                        if w % 2 == 0:                # x at rank w last, xb at w+1 first
                            c, d = x, xb
                        else:                         # xb at rank w last, x at w+1 first
                            c, d = xb, x
                        u = self.new()
                        for z in C:
                            if z != c and popcount(z) % 2 == popcount(c) % 2:
                                add([-u, self.o(w, z, c)])
                            if z != d and popcount(z) % 2 == popcount(d) % 2:
                                add([-u, self.o(w + 1, d, z)])
                        ors.append(u)
                    add(ors)
        if sym:
            for j, l in itertools.combinations(range(n), 2):
                if (1 << j) ^ (1 << l) in S:
                    add([self.o(0, (1 << j) ^ (1 << l), 0)])
            for i in range(n - 1):
                if 1 << i in S and 1 << (i + 1) in S:
                    add([self.o(1, 1 << i, 1 << (i + 1))])
        return self

    def write(self, path):
        with open(path, "w") as f:
            f.write(f"p cnf {len(self.var)} {len(self.clauses)}\n")
            for c in self.clauses:
                f.write(" ".join(map(str, c)) + " 0\n")


if __name__ == "__main__":
    n, k, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    R = PFRP(n, k).build()
    R.write(out)
    print(f"PFR+({n},{k}): {len(R.var)} vars {len(R.clauses)} clauses -> {out}")
