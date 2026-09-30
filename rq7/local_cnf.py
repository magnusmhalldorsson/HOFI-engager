#!/usr/bin/env python3
"""
The *distance-local relaxation* of event_cnf.py: only event pairs of vertices at Hamming
distance <= D get variables, and only the clauses all of whose literals are such variables
(or forced constants) are kept.  Dropping clauses from a CNF that every normalised
representant satisfies gives a CNF that every normalised representant still satisfies, so
unsatisfiability of the relaxation still proves that no k-uniform representant exists.

Clause families (as in event_cnf.py, restricted to distance <= D):
  closure   [f' < e] -> [f < e] for an edge step f -> f' (both undetermined w.r.t. e);
  tri       no directed 3-cycle among three pairwise undetermined events whose vertices are
            pairwise at distance <= D (full transitivity inside this range);
  nonalt    for every non-edge ab with d(a,b) in DSET (default: 2..D);
  sym       (e_i, 1) < (e_{i+1}, 1), and no letter w with |w| <= D occurs twice inside the
            arc (0,0) -> (0,2).

Usage: python3 local_cnf.py N K D [--dset 2,3] -o out.cnf
"""
import argparse
import itertools

from event_cnf import EventCNF, popcount


class LocalCNF(EventCNF):
    def __init__(self, n, k, D, dset=None, shortest=True):
        super().__init__(n, k, shortest=shortest)
        self.D = D
        self.dset = set(range(2, D + 1)) if dset is None else set(dset)

    def before(self, a, r, b, s):
        if a != b and popcount(a ^ b) > self.D and abs(s - r) < popcount(a ^ b):
            return None                       # undetermined pair outside the local range
        return super().before(a, r, b, s)

    @staticmethod
    def neg(l):
        return None if l is None else EventCNF.neg(l)

    def add(self, lits):
        if any(l is None for l in lits):
            return
        super().add(lits)

    def undetermined(self, c, t):
        return [(a, s) for (a, s) in super().undetermined(c, t) if popcount(a ^ c) <= self.D]

    def nonalt(self):
        for a, b in itertools.combinations(self.V, 2):
            d = popcount(a ^ b)
            if d < 2 or d not in self.dset or d > self.D:
                continue
            ors = []
            for dl in range(-(d - 2), d - 1, 2):
                lits = [self.before(b, r + dl, a, r) for r in self.ranks(a)]
                y = self._new(("nc", a, b, dl))
                self.add([-y] + lits)
                self.add([-y] + [self.neg(l) for l in lits])
                ors.append(y)
            self.add(ors)

    def triangles(self, mode):
        assert mode == "all"
        for c in self.V:
            for t in self.ranks(c):
                und = self.undetermined(c, t)
                for (a, r), (b, s) in itertools.combinations(und, 2):
                    if a == b or a < c or b < c:
                        continue
                    dab = popcount(a ^ b)
                    if dab > self.D or abs(s - r) >= dab:
                        continue
                    x1, x2, x3 = self.before(c, t, a, r), self.before(a, r, b, s), self.before(b, s, c, t)
                    self.add([self.neg(x1), self.neg(x2), self.neg(x3)])
                    self.add([x1, x2, x3])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("k", type=int)
    ap.add_argument("D", type=int)
    ap.add_argument("--dset", default=None)
    ap.add_argument("--no-shortest", action="store_true")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    dset = None if a.dset is None else [int(x) for x in a.dset.split(",")]
    E = LocalCNF(a.n, a.k, a.D, dset=dset, shortest=not a.no_shortest).build("all")
    E.write(a.out)
    print(f"Q_{a.n} k={a.k} D={a.D}: {len(E.var)} variables, {len(E.clauses)} clauses -> {a.out}")
