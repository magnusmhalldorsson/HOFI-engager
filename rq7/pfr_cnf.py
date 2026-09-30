#!/usr/bin/env python3
"""
Permutation-field relaxation PFR(n, k): only the orders of same-rank events at distance 2.

For a vertex y and its arc from (y, s) to (y, s+2), the neighbours b_i = y + e_i fire once
each, at rank s+1; pi = their order.  t_jl = y + e_j + e_l is at distance 2 from y.
Necessary conditions (README, sec. 6b):
 (E) x, y at distance 2: their order is not the same in all k rounds of their parity;
 (C) for the diagonal (b_i, t_jl) of the cube y + span(e_i, e_j, e_l): some arc (s -> s+2) of y
     with   b_j, b_l before b_i (rank s+1) and t_jl before y (rank s+2)   [cone bottom b_i]
     or     b_i before b_j, b_l (rank s+1) and y before t_jl (rank s)     [cone bottom t_jl];
 (D) for the diagonal (y, y + e_T): some rank s of y in which all three t_jl ({j,l} in T) come
     before y, or all three come after y;
 (tri) transitivity among three pairwise distance-2 events of equal rank.
Symmetry: (0,0) follows all of its distance-2 vertices in rank 0 (translation: take the last
rank-0 event); the neighbours of 0 fire in the order e_1, ..., e_n at rank 1.
Usage: python3 pfr_cnf.py N K -o out.cnf
"""
import argparse
import itertools


def popcount(x):
    return bin(x).count("1")


class PFR:
    def __init__(self, n, k):
        self.n, self.k, self.P = n, k, 2 * k
        self.N = 1 << n
        self.var = {}
        self.clauses = []

    def v(self, key):
        if key not in self.var:
            self.var[key] = len(self.var) + 1
        return self.var[key]

    def o(self, s, a, b):
        """(a, s) before (b, s); a, b at distance 2, of parity s"""
        s %= self.P
        assert popcount(a ^ b) == 2 and popcount(a) % 2 == s % 2
        return self.v(("o", s, a, b)) if a < b else -self.v(("o", s, b, a))

    def new(self):
        return self.v(("aux", len(self.var)))

    def build(self):
        n, P, N = self.n, self.P, self.N
        add = self.clauses.append
        # transitivity on triangles of the halved cube, every rank
        for s in range(P):
            for y in range(N):
                if popcount(y) % 2 == s % 2:
                    continue
                nb = [y ^ (1 << i) for i in range(n)]      # pairwise at distance 2
                for a, b, c in itertools.permutations(nb, 3):
                    add([-self.o(s, a, b), -self.o(s, b, c), self.o(s, a, c)])
        # (E)
        for a in range(N):
            for i, j in itertools.combinations(range(n), 2):
                b = a ^ (1 << i) ^ (1 << j)
                if a > b:
                    continue
                rs = [s for s in range(P) if s % 2 == popcount(a) % 2]
                add([self.o(s, a, b) for s in rs])
                add([-self.o(s, a, b) for s in rs])
        for y in range(N):
            ranks = [s for s in range(P) if s % 2 == popcount(y) % 2]
            b = [y ^ (1 << i) for i in range(n)]
            t = lambda j, l: y ^ (1 << j) ^ (1 << l)
            # (C)
            for i in range(n):
                for j, l in itertools.combinations([x for x in range(n) if x != i], 2):
                    ors = []
                    for s in ranks:
                        u, w = self.new(), self.new()
                        add([-u, self.o(s + 1, b[j], b[i])]); add([-u, self.o(s + 1, b[l], b[i])])
                        add([-u, self.o(s + 2, t(j, l), y)])
                        add([-w, self.o(s + 1, b[i], b[j])]); add([-w, self.o(s + 1, b[i], b[l])])
                        add([-w, self.o(s, y, t(j, l))])
                        ors += [u, w]
                    add(ors)
            # (D)
            for T in itertools.combinations(range(n), 3):
                ors = []
                for s in ranks:
                    u, w = self.new(), self.new()
                    for j, l in itertools.combinations(T, 2):
                        add([-u, self.o(s, t(j, l), y)]); add([-w, self.o(s, y, t(j, l))])
                    ors += [u, w]
                add(ors)
        # symmetry breaking
        for j, l in itertools.combinations(range(n), 2):
            add([self.o(0, (1 << j) ^ (1 << l), 0)])
        for i in range(n - 1):
            add([self.o(1, 1 << i, 1 << (i + 1))])
        return self

    def write(self, path):
        with open(path, "w") as f:
            f.write(f"p cnf {len(self.var)} {len(self.clauses)}\n")
            for c in self.clauses:
                f.write(" ".join(map(str, c)) + " 0\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("k", type=int)
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    R = PFR(a.n, a.k).build()
    R.write(a.out)
    print(f"PFR({a.n},{a.k}): {len(R.var)} variables, {len(R.clauses)} clauses -> {a.out}")
