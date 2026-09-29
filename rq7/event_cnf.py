#!/usr/bin/env python3
"""
CNF whose unsatisfiability shows that the hypercube Q_n has no k-uniform word-representant.

Background (see README.md for the proofs).  If a k-uniform word w represents Q_n, then

  * (height function)  one can attach to every letter-occurrence of w an integer *rank*
    so that the occurrence of x of rank r is followed, among the occurrences of x, by the
    one of rank r+2; ranks of x have the parity of |x| (Hamming weight); and for every
    edge xy the occurrences satisfy  (y,r-1) < (x,r) < (y,r+1).  Here (x,r) denotes the
    occurrence ("event") of x with rank r, and < is the order of the bi-infinite word
    w w w ...; the order is periodic: (x,r) < (y,s)  iff  (x,r+2k) < (y,s+2k).

  * (light cone)  consequently (x,r) < (y,s) whenever s - r >= d(x,y) (Hamming distance).
    Only pairs with |s-r| < d(x,y) are undetermined; they are the variables.

  * (non-alternation)  for a non-edge xy with d = d(x,y) >= 2, the number
        g(r) = #{ s : |s-r| < d, (y,s) < (x,r) }
    is not constant over the k ranks r of x in one period (x and y alternate in w iff g is
    constant).

  * (normalisation)  after an automorphism of Q_n and a shift of all ranks we may assume
    that the arc of the letter 0 between its events (0,0) and (0,2) is a globally shortest
    arc of w -- so no letter occurs twice inside it -- and that the neighbours
    e_1,...,e_n of 0 occur inside it in this order.

Clauses (every one of them holds for the event order of a normalised representant):
  closure   for each event e and each edge step f=(a,r) -> f'=(b,r+1) (ab an edge) with
            both f, f' undetermined relative to e:     [f' < e]  ->  [f < e]
            (this is transitivity through the forced relation f < f');
  nonalt    for each non-edge ab: some offset dl in {-(d-2), ..., d-2} (step 2) such that
            r -> [(b, r+dl) < (a, r)] is non-constant over the k ranks of a
            (g is the sum of these indicators, so g non-constant forces one of them to be);
  sym       (e_i, 1) < (e_{i+1}, 1),  and no vertex has two consecutive events inside the
            arc (0,0) -> (0,2);
  tri       [optional] no directed 3-cycle among three pairwise undetermined events:
            --tri samerank   only for three events of equal rank,
            --tri all        for all such triples (full transitivity).
With --tri all the CNF is equivalent to the existence of a normalised representant;
the weaker variants are relaxations, so their unsatisfiability is still a proof.

Usage:  python3 event_cnf.py N K --tri {none,samerank,all} [--no-shortest] -o out.cnf
The variable map (event pair -> variable number) is written to out.cnf.vars.
"""
import argparse
import itertools
import sys


def popcount(x):
    return bin(x).count("1")


class EventCNF:
    def __init__(self, n, k, shortest=True):
        self.n, self.k, self.P = n, k, 2 * k
        self.V = list(range(1 << n))
        self.shortest = shortest
        self.var = {}          # canonical key -> variable number
        self.clauses = []

    # --- literals -----------------------------------------------------------------
    def _new(self, key):
        v = self.var.get(key)
        if v is None:
            v = len(self.var) + 1
            self.var[key] = v
        return v

    def before(self, a, r, b, s):
        """(a,r) < (b,s):  True/False if forced, otherwise a signed variable."""
        if a == b:
            return r < s
        d = popcount(a ^ b)
        if s - r >= d:
            return True
        if r - s >= d:
            return False
        sign = 1
        if a > b:
            a, r, b, s, sign = b, s, a, r, -1
        q = r - r % self.P                      # periodicity: normalise r into [0, P)
        return sign * self._new(("lt", a, r - q, b, s - q))

    @staticmethod
    def neg(l):
        return (not l) if isinstance(l, bool) else -l

    def add(self, lits):
        c = []
        for l in lits:
            if l is True:
                return
            if l is False:
                continue
            c.append(l)
        if not c:
            raise ValueError("empty clause generated")
        self.clauses.append(c)

    # --- structure ----------------------------------------------------------------
    def ranks(self, v):
        return [r for r in range(self.P) if r % 2 == popcount(v) % 2]

    def undetermined(self, c, t):
        """events (a, s) whose order relative to (c, t) is not forced by the light cone"""
        out = []
        for a in self.V:
            if a == c:
                continue
            d = popcount(a ^ c)
            for s in range(t - d + 1, t + d):
                if (s - popcount(a)) % 2 == 0:
                    out.append((a, s))
        return out

    # --- clause families ----------------------------------------------------------
    def closure(self):
        for c in self.V:
            for t in self.ranks(c):
                und = set(self.undetermined(c, t))
                for (a, r) in und:
                    for i in range(self.n):
                        b = a ^ (1 << i)
                        if (b, r + 1) in und:
                            self.add([self.neg(self.before(b, r + 1, c, t)), self.before(a, r, c, t)])

    def nonalt(self):
        for a, b in itertools.combinations(self.V, 2):
            d = popcount(a ^ b)
            if d < 2:
                continue
            ors = []
            for dl in range(-(d - 2), d - 1, 2):
                lits = [self.before(b, r + dl, a, r) for r in self.ranks(a)]
                y = self._new(("nc", a, b, dl))
                self.add([-y] + lits)
                self.add([-y] + [self.neg(l) for l in lits])
                ors.append(y)
            self.add(ors)

    def symmetry(self):
        for i in range(self.n - 1):
            self.add([self.before(1 << i, 1, 1 << (i + 1), 1)])
        if self.shortest:
            for w in self.V:
                if w == 0:
                    continue
                d = popcount(w)
                for s in range(-d - 2, d + 3):
                    if (s - d) % 2:
                        continue
                    l1 = self.before(0, 0, w, s)
                    l2 = self.before(w, s + 2, 0, 2)
                    if l1 is False or l2 is False:
                        continue
                    self.add([self.neg(l1), self.neg(l2)])

    def triangles(self, mode):
        if mode == "none":
            return
        if mode == "samerank":
            for par in (0, 1):
                cls = [v for v in self.V if popcount(v) % 2 == par]
                for r in range(par, self.P, 2):
                    for a, b, c in itertools.combinations(cls, 3):
                        x1, x2, x3 = self.before(a, r, b, r), self.before(b, r, c, r), self.before(c, r, a, r)
                        self.add([self.neg(x1), self.neg(x2), self.neg(x3)])
                        self.add([x1, x2, x3])
            return
        assert mode == "all"
        for c in self.V:
            for t in self.ranks(c):
                und = self.undetermined(c, t)
                for (a, r), (b, s) in itertools.combinations(und, 2):
                    # each triangle once: (c,t) is the event of the smallest vertex, t in [0,P)
                    if a == b or a < c or b < c:
                        continue
                    if abs(s - r) >= popcount(a ^ b):
                        continue
                    x1, x2, x3 = self.before(c, t, a, r), self.before(a, r, b, s), self.before(b, s, c, t)
                    self.add([self.neg(x1), self.neg(x2), self.neg(x3)])
                    self.add([x1, x2, x3])

    def build(self, tri="none"):
        self.closure()
        self.nonalt()
        self.symmetry()
        self.triangles(tri)
        return self

    def write(self, path):
        with open(path, "w") as f:
            f.write(f"p cnf {len(self.var)} {len(self.clauses)}\n")
            for c in self.clauses:
                f.write(" ".join(map(str, c)) + " 0\n")
        with open(path + ".vars", "w") as f:
            for key, v in sorted(self.var.items(), key=lambda kv: kv[1]):
                f.write(f"{v} {' '.join(map(str, key))}\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("n", type=int)
    ap.add_argument("k", type=int)
    ap.add_argument("--tri", choices=["none", "samerank", "all"], default="none")
    ap.add_argument("--no-shortest", action="store_true", help="omit the shortest-arc normalisation")
    ap.add_argument("-o", "--out", required=True)
    A = ap.parse_args(argv)
    E = EventCNF(A.n, A.k, shortest=not A.no_shortest).build(A.tri)
    E.write(A.out)
    print(f"Q_{A.n}, k={A.k}, tri={A.tri}: {len(E.var)} variables, {len(E.clauses)} clauses -> {A.out}")


if __name__ == "__main__":
    main()
