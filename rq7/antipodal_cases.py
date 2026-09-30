#!/usr/bin/env python3
"""
Exhaustive case split on the maximum antipodal lag, used for the Q_7 computation.

For an event (x, r) let  A_x(r) = H_{x,r}(x')  be the lag of the antipode x' = x XOR 1...1 as
seen at that event:  A_x(r) = 2 g(r) - (n-2)  where g(r) is the number of the n-1 undetermined
events of x' (ranks r-(n-2), ..., r+(n-2), step 2) that precede (x, r).

Lemma.  M := max_{x,r} A_x(r) >= 2 if n is even and >= 3 if n is odd.
Proof.  For a fixed antipodal pair {x, x'} each of the k(n-1) undetermined event pairs per period
is counted exactly once, either in some g_{x,x'}(r) or in some g_{x',x}(s).  So the 2k values
g have average (n-1)/2, i.e. the lags have average 1.  If all lags were <= 1 they would all
equal 1, so g_{x,x'} would be constant and x, x' would alternate -- impossible, since they are
not adjacent (n >= 2).  Lags have the parity of n.  QED

So for n = 7 exactly one of the following holds, and each case admits the stated normalisation
(all conditions are invariant under Aut(Q_n) and under shifting all ranks by an even number):

  case I   (M = 3):  every lag is <= 3.  Normalise the globally shortest arc to (0,0) -> (0,2)
                     exactly as in event_cnf.py (the bound is invariant, so this is allowed).
  case II  (M = 5):  every lag is <= 5, and the maximum 5 is attained at the event (0,0).
  case III (M = 7):  the lag 7 is attained at (0,0).
In cases II and III the maximiser is moved to (0,0) by a translation and a rank shift, and the
coordinates are then permuted so that e_1,...,e_n occur in order inside the arc (0,0)->(0,2).

Refinement ("maximum then drop").  In cases II and III we may moreover assume A_0(2) = M - 2.
Indeed A_x(r+2) >= A_x(r) - 2 always (the antipode's next rank never decreases), so an event
with A_x(r) = M is followed by A_x(r+2) in {M-2, M}; if every maximiser were followed by a
maximiser, A_x would be constantly M and x, x' would alternate.  So choose a maximiser
(x, r) with A_x(r+2) = M - 2 and move it to (0,0).  (Equivalently: the antipode does not
occur inside the arc (0,0) -> (0,2).)

Usage:  python3 antipodal_cases.py N K CASE -o out.cnf        (CASE in I, II, III)
"""
import argparse

from event_cnf import EventCNF


def add_bound(E, M):
    """all antipodal lags <= M:  the (g+1)-th undetermined antipodal event follows (x, r)."""
    n = E.n
    full = (1 << n) - 1
    g = (M + n - 2) // 2
    if g > n - 2:
        return
    for x in E.V:
        for r in E.ranks(x):
            E.add([E.before(x, r, x ^ full, r - (n - 2) + 2 * g)])


def add_value_at_origin(E, M):
    """A_0(0) = M"""
    n = E.n
    full = (1 << n) - 1
    g = (M + n - 2) // 2
    if g >= 1:
        E.add([E.before(full, -(n - 2) + 2 * (g - 1), 0, 0)])
    if g <= n - 2:
        E.add([E.before(0, 0, full, -(n - 2) + 2 * g)])


def add_drop_at_origin(E, M):
    """A_0(2) = M - 2, given A_0(0) = M: the antipode's event of rank M follows (0, 2)"""
    full = (1 << E.n) - 1
    E.add([E.before(0, 2, full, M)])


def build(n, k, case, tri="samerank", drop=True):
    assert n % 2 == 1, "the three-case split is stated for odd n"
    lo = 3
    Ms = {"I": lo, "II": lo + 2, "III": lo + 4}
    M = Ms[case]
    assert M <= n, "case not possible for this n"
    E = EventCNF(n, k, shortest=(case == "I"))
    E.closure()
    E.nonalt()
    E.symmetry()
    E.triangles(tri)
    if case == "I":
        add_bound(E, M)
    else:
        if M < n:
            add_bound(E, M)
        add_value_at_origin(E, M)
        if drop:
            add_drop_at_origin(E, M)
    return E


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("n", type=int)
    ap.add_argument("k", type=int)
    ap.add_argument("case", choices=["I", "II", "III"])
    ap.add_argument("--tri", choices=["none", "samerank", "all"], default="samerank")
    ap.add_argument("--no-drop", action="store_true", help="omit the A_0(2) = M-2 refinement")
    ap.add_argument("-o", "--out", required=True)
    A = ap.parse_args()
    E = build(A.n, A.k, A.case, A.tri, drop=not A.no_drop)
    E.write(A.out)
    print(f"Q_{A.n}, k={A.k}, case {A.case}: {len(E.var)} variables, {len(E.clauses)} clauses -> {A.out}")


if __name__ == "__main__":
    main()
