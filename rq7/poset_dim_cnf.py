#!/usr/bin/env python3
"""
CNF for dim(P_n) <= d, where P_n is the height-2 poset of Q_n: x < y iff x is even, y is odd and
xy is an edge.  Variables: for each of the d linear orders and each incomparable pair, which
element comes first; clauses: transitivity of each order (comparable pairs are forced
constants: even below odd), and every incomparable pair occurs in both orders in some two of
the d linear extensions.

Relevance.  If L_1, ..., L_d realise P_n, the word L_1 L_2 ... L_d (a concatenation of
permutations of V(Q_n)) is d-uniform, and two letters alternate in it iff they are ordered the
same way by every L_i, i.e. iff they are comparable in P_n, i.e. iff they are adjacent.  So
dim(P_n) <= d gives a (permutational) d-representant of Q_n.  Conversely such a representant
with d = 4 would be a special solution of WR(n, 4) in which no window of odd rank has an
inversion.

Result (kissat): satisfiable for (n, d) = (3, 4), (4, 4); unsatisfiable for (5, 4).  Since P_5
is an induced subposet of P_n for n >= 5, no Q_n with n >= 5 has a permutational 4-representant;
in particular a 4-representant of Q_7, if one existed, could not be of this form.

Usage: python3 poset_dim_cnf.py N D -o out.cnf
"""
import argparse
import itertools


def popcount(x):
    return bin(x).count("1")


def build(n, d):
    N = 1 << n
    var, clauses = {}, []

    def lt(i, a, b):
        if popcount(a ^ b) == 1:
            return popcount(a) % 2 == 0          # even below odd
        if a > b:
            return -lt(i, b, a)
        return var.setdefault((i, a, b), len(var) + 1)

    def add(lits):
        c = []
        for l in lits:
            if l is True:
                return
            if l is not False:
                c.append(l)
        clauses.append(c)

    neg = lambda l: (not l) if isinstance(l, bool) else -l
    for i in range(d):
        for a, b, c in itertools.combinations(range(N), 3):
            x1, x2, x3 = lt(i, a, b), lt(i, b, c), lt(i, c, a)
            add([neg(x1), neg(x2), neg(x3)])
            add([x1, x2, x3])
    for a, b in itertools.combinations(range(N), 2):
        if popcount(a ^ b) != 1:
            add([lt(i, a, b) for i in range(d)])
            add([lt(i, b, a) for i in range(d)])
    return var, clauses


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int)
    ap.add_argument("d", type=int)
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    var, clauses = build(a.n, a.d)
    with open(a.out, "w") as f:
        f.write(f"p cnf {len(var)} {len(clauses)}\n")
        for c in clauses:
            f.write(" ".join(map(str, c)) + " 0\n")
    print(f"dim(P_{a.n}) <= {a.d}: {len(var)} variables, {len(clauses)} clauses -> {a.out}")
