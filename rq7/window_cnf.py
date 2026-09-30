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
    def __init__(self, n, k, dset=(2, 3), norm="shortest"):
        super().__init__(n, k, shortest=(norm == "shortest"))
        self.dset = set(dset)
        self.norm = norm

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
        """transitivity in every window (ranks r, r+1): each triangle once -- triangles
        inside a single rank are generated only in the window where that rank comes first"""
        P = self.P
        for r in range(P):
            ev = [(v, r) for v in self.V if popcount(v) % 2 == r % 2] + \
                 [(v, r + 1) for v in self.V if popcount(v) % 2 == (r + 1) % 2]
            for e1, e2, e3 in itertools.combinations(ev, 3):
                if e1[1] == e2[1] == e3[1] == r + 1:
                    continue
                x1 = self.before(e1[0], e1[1], e2[0], e2[1])
                x2 = self.before(e2[0], e2[1], e3[0], e3[1])
                x3 = self.before(e3[0], e3[1], e1[0], e1[1])
                self.add([self.neg(x1), self.neg(x2), self.neg(x3)])
                self.add([x1, x2, x3])

    def lag_normalisation(self):
        """(0,0) is an event of maximal lag t(x,r) - (L/2k) r: every event of rank <= 0
        precedes it (see README)"""
        for v in self.V:
            if v == 0:
                continue
            r = 0 if popcount(v) % 2 == 0 else -1
            self.add([self.before(v, r, 0, 0)])

    def rho(self, key):
        """time reversal composed with reversing the coordinate order:
        (a, r) < (b, s)  |->  (pi b, 2 - s) < (pi a, 2 - r).  It maps the CNF (with the
        shortest-arc normalisation) onto itself: windows to windows, the arc (0,0)->(0,2) to
        itself, and the neighbour order e_1 < ... < e_n to itself."""
        _, a, r, b, s = key
        pi = lambda v: sum(1 << (self.n - 1 - i) for i in range(self.n) if v >> i & 1)
        return self.before(pi(b), 2 - s, pi(a), 2 - r)

    def reversal_lex(self, m):
        """lex-leader constraint X <=_lex rho(X) on the first m variables of the view of (0,0)
        (valid because rho is a symmetry of the CNF and an involution)"""
        X, Y = [], []
        for y in sorted(self.V, key=lambda v: (popcount(v), v)):
            for s in range(-1, 2):
                if y == 0 or (s - popcount(y)) % 2 or len(X) >= m:
                    continue
                l = self.before(y, s, 0, 0)
                if isinstance(l, bool) or l is None:
                    continue
                key = ("lt",) + next(k[1:] for k, v in self.var.items() if v == abs(l))
                X.append(abs(l)); Y.append(self.rho(key))
        # X <=_lex Y  <=>  Y >=_lex X
        self.lex_leq(X, Y)

    def lex_leq(self, X, Y):
        """X <=_lex Y (false < true)"""
        eq = None
        for i, (x, y) in enumerate(zip(X, Y)):
            if isinstance(y, bool):
                raise ValueError("forced literal in lex constraint")
            pre = [] if eq is None else [-eq]
            self.add(pre + [-x, y])                   # prefix equal -> not (x > y)
            if i == len(X) - 1:
                break
            e = self._new(("lexeq", i))
            self.add(pre + [-x, -y, e])
            self.add(pre + [x, y, e])
            eq = e

    def build(self, revlex=0):
        self.windows()
        self.nonalt()
        self.symmetry()
        if self.norm == "lag":
            self.lag_normalisation()
        if revlex:
            assert self.norm == "shortest"
            self.reversal_lex(revlex)
        return self


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("k", type=int)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--norm", choices=["shortest", "lag"], default="shortest")
    ap.add_argument("--revlex", type=int, default=0,
                    help="break time reversal by a lex-leader constraint on this many variables")
    a = ap.parse_args()
    E = WindowCNF(a.n, a.k, norm=a.norm).build(revlex=a.revlex)
    E.write(a.out)
    print(f"WR({a.n},{a.k}): {len(E.var)} variables, {len(E.clauses)} clauses -> {a.out}")
