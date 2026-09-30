#!/usr/bin/env python3
"""
The *window relaxation* WR(n, k, DSET): the part of the event order of a k-uniform
representant of Q_n that involves only events of equal or adjacent ranks.

For every rank r (mod 2k) the events of rank r and r+1 form a *window*; the event order
restricted to a window is a linear order.  Variables: one per undetermined pair of events
with rank difference 0 or 1 (every such pair is undetermined unless the two vertices are
adjacent).  Clauses:
  tri     transitivity inside every window (three events of ranks in {r, r+1}), where the
          relation (y, r) < (z, r+1) for adjacent y, z is a forced constant;
  nonalt  non-alternation of the pairs at distances in DSET (default {2, 3}; only distances
          2 and 3 are expressible with rank differences <= 1);
  sym     (e_i, 1) < (e_{i+1}, 1), and no letter occurs twice inside the arc (0,0)->(0,2)
          (only the clauses whose literals are window pairs are kept).
Every clause is a clause of event_cnf.py --tri all (restricted), so an unsatisfiable WR
still proves that no k-uniform representant exists.

Usage: python3 window_cnf.py N K -o out.cnf
"""
import argparse
import itertools

from event_cnf import EventCNF, popcount


class WindowCNF(EventCNF):
    def __init__(self, n, k, dset=(2, 3), shortest=True):
        super().__init__(n, k, shortest=shortest)
        self.dset = set(dset)

    def before(self, a, r, b, s):
        if a != b and abs(s - r) >= 2 and abs(s - r) < popcount(a ^ b):
            return None
        return super().before(a, r, b, s)

    @staticmethod
    def neg(l):
        return None if l is None else EventCNF.neg(l)

    def add(self, lits):
        if any(l is None for l in lits):
            return
        super().add(lits)

    def nonalt(self):
        for a, b in itertools.combinations(self.V, 2):
            d = popcount(a ^ b)
            if d < 2 or d not in self.dset:
                continue
            assert d <= 3
            ors = []
            for dl in range(-(d - 2), d - 1, 2):
                lits = [self.before(b, r + dl, a, r) for r in self.ranks(a)]
                y = self._new(("nc", a, b, dl))
                self.add([-y] + lits)
                self.add([-y] + [self.neg(l) for l in lits])
                ors.append(y)
            self.add(ors)

    def windows(self):
        n, P = self.n, self.P
        for r in range(P):
            ev = [(v, r) for v in self.V if popcount(v) % 2 == r % 2] + \
                 [(v, r + 1) for v in self.V if popcount(v) % 2 == (r + 1) % 2]
            # each triangle of the window once; skip triangles lying inside a single rank
            # except for r even... (rank-r triangles are generated in window (r, r+1) only)
            for e1, e2, e3 in itertools.combinations(ev, 3):
                x1 = self.before(e1[0], e1[1], e2[0], e2[1])
                x2 = self.before(e2[0], e2[1], e3[0], e3[1])
                x3 = self.before(e3[0], e3[1], e1[0], e1[1])
                if any(isinstance(x, bool) for x in (x1, x2, x3)):
                    # at least one forced relation: keep only the non-trivial implications
                    self.add([self.neg(x1), self.neg(x2), self.neg(x3)])
                    self.add([x1, x2, x3])
                else:
                    self.add([self.neg(x1), self.neg(x2), self.neg(x3)])
                    self.add([x1, x2, x3])

    def build(self):
        self.windows()
        self.nonalt()
        self.symmetry()
        return self


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("k", type=int)
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    E = WindowCNF(a.n, a.k).build()
    E.write(a.out)
    print(f"WR({a.n},{a.k}): {len(E.var)} variables, {len(E.clauses)} clauses -> {a.out}")
