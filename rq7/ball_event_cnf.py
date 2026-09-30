#!/usr/bin/env python3
"""
The event CNF of event_cnf.py (all distances, full transitivity) restricted to the events of
a vertex set S, with the lag normalisation of window_cnf.py: (0,0) maximises the lag, so every
event of rank <= 0 precedes it; then the neighbours of 0 are sorted in rank 1.

Soundness.  Forced relations are computed with distances in Q_n (not in the subgraph S), so
every kept clause is a clause of event_cnf.py --tri all whose events all belong to S, or a
lag-normalisation unit; each of them holds in the lag-normalised event order of any k-uniform
representant of Q_n.  This is true for every vertex set S; balls around 0 are used because 0
carries the normalisation.  An unsatisfiable restriction therefore still proves that Q_n is not
k-representable.

Usage: python3 ball_event_cnf.py N K R -o out.cnf
"""
import argparse
import itertools

from event_cnf import EventCNF, popcount


class BallEventCNF(EventCNF):
    def __init__(self, n, k, S):
        super().__init__(n, k, shortest=False)
        self.S = set(S)
        self.V = sorted(self.S)            # every clause family iterates over self.V

    def before(self, a, r, b, s):
        if a != b and (a not in self.S or b not in self.S):
            l = super().before(a, r, b, s)
            return l if isinstance(l, bool) else None
        return super().before(a, r, b, s)

    @staticmethod
    def neg(l):
        return None if l is None else EventCNF.neg(l)

    def add(self, lits):
        if any(l is None for l in lits):
            return
        super().add(lits)

    def lag_normalisation(self):
        for v in self.V:
            if v == 0:
                continue
            for s in range(-self.P, 1):
                if (s - popcount(v)) % 2 == 0:
                    self.add([self.before(v, s, 0, 0)])

    def build(self):
        self.closure()
        self.nonalt()
        self.symmetry()                    # neighbour order in rank 1 (shortest-arc part is off)
        self.lag_normalisation()
        self.triangles("all")
        return self


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("k", type=int)
    ap.add_argument("R", type=int)
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    S = [v for v in range(1 << a.n) if popcount(v) <= a.R]
    E = BallEventCNF(a.n, a.k, S).build()
    E.write(a.out)
    print(f"Q_{a.n} k={a.k} ball B_{a.R}(0) ({len(S)} vertices): {len(E.var)} variables, "
          f"{len(E.clauses)} clauses -> {a.out}")
