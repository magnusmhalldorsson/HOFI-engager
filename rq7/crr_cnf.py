#!/usr/bin/env python3
"""
Coupled round relaxation CRR(n, k): a relaxation of the window CNF (window_cnf.py) that keeps
only the orders inside single ranks ("rounds").

For every rank r in Z_{2k}, <_r is the order of the events of rank r (vertices of parity r).
Conditions, all necessary for the event order of a k-uniform representant:
 (E)  x, y at distance 2: not the same order in all k rounds of their parity  [(E4), d = 2];
 (T*) x, z at distance 3: some window w (ranks w, w+1) in which the vertex c of parity w
      follows every neighbour of the other vertex d in <_w, and d precedes every neighbour of
      c in <_{w+1}.
      Reason: by (E4) the view v_{x,r}(z) is not constant, so some window w has an inversion
      (d, w+1) < (c, w).  Then (y, w) < (d, w+1) < (c, w) for y in N(d), and
      (d, w+1) < (c, w) < (u, w+1) for u in N(c).
Symmetry breaking: translation makes (0,0) the last rank-0 event; coordinate permutations
order the neighbours of 0 in round 1.  (Both are invariant under the other's group.)
Usage: python3 crr_cnf.py N K -o out.cnf
"""
import argparse
import itertools


def popcount(x):
    return bin(x).count("1")


class CRR:
    def __init__(self, n, k):
        self.n, self.k, self.P = n, k, 2 * k
        self.V = list(range(1 << n))
        self.nv = 0
        self.var = {}
        self.clauses = []

    def new(self, key=None):
        self.nv += 1
        if key is not None:
            self.var[key] = self.nv
        return self.nv

    def o(self, r, a, b):
        """a before b in round r (a, b of parity r)"""
        r %= self.P
        if a < b:
            key = (r, a, b)
            return self.var[key] if key in self.var else self.new(key)
        return -self.o(r, b, a)

    def build(self):
        n, P = self.n, self.P
        add = self.clauses.append
        for r in range(P):
            cls = [v for v in self.V if popcount(v) % 2 == r % 2]
            for a, b, c in itertools.combinations(cls, 3):
                add([-self.o(r, a, b), -self.o(r, b, c), self.o(r, a, c)])
                add([self.o(r, a, b), self.o(r, b, c), -self.o(r, a, c)])
        for a, b in itertools.combinations(self.V, 2):
            if popcount(a ^ b) == 2:
                rs = [r for r in range(P) if r % 2 == popcount(a) % 2]
                add([self.o(r, a, b) for r in rs])
                add([-self.o(r, a, b) for r in rs])
        for a, b in itertools.combinations(self.V, 2):
            if popcount(a ^ b) != 3:
                continue
            ors = []
            for w in range(P):
                c, d = (a, b) if popcount(a) % 2 == w % 2 else (b, a)
                y = self.new()
                for i in range(n):
                    add([-y, self.o(w, d ^ (1 << i), c)])       # N(d) before c in round w
                    add([-y, self.o(w + 1, d, c ^ (1 << i))])   # d before N(c) in round w+1
                ors.append(y)
            add(ors)
        for v in self.V:                                            # (0,0) last in round 0
            if v and popcount(v) % 2 == 0:
                add([self.o(0, v, 0)])
        for i in range(n - 1):                                       # neighbour order, round 1
            add([self.o(1, 1 << i, 1 << (i + 1))])
        return self

    def write(self, path):
        with open(path, "w") as f:
            f.write(f"p cnf {self.nv} {len(self.clauses)}\n")
            for c in self.clauses:
                f.write(" ".join(map(str, c)) + " 0\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("k", type=int)
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    R = CRR(a.n, a.k).build()
    R.write(a.out)
    print(f"CRR({a.n},{a.k}): {R.nv} variables, {len(R.clauses)} clauses -> {a.out}")
