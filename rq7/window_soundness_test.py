#!/usr/bin/env python3
"""
Soundness tests for window_cnf.py, crr_cnf.py, pfr_cnf.py and pfrp_cnf.py: every clause must be satisfied by (the
normalised event order of) every genuine representant.

For each word w that represents Q_n (checked from the definition by check_word.py):
  * WR, normalisation 'shortest' (sec. 4), optionally with the time-reversal lex-leader
    constraint: the normalised order X or its reverse rho(X) satisfies every clause
    (rho is a symmetry of the CNF, see window_cnf.py);
  * WR, normalisation 'lag': (0,0) is an event of maximal lag;
  * CRR, PFR and PFR+: (0,0) is the last rank-0 event, neighbours of 0 in order.
Usage: python3 window_soundness_test.py N WORDFILE [N WORDFILE ...]
"""
import itertools
import sys

from check_word import represents_Qn
from crr_cnf import CRR
from pfr_cnf import PFR
from pfrp_cnf import PFRP
from event_cnf import popcount
from soundness_test import event_positions, normalise
from window_cnf import WindowCNF


def rotate_translate_sort(w, n, p, x):
    """start the word at position p (an occurrence of x), translate by x, sort coordinates"""
    w2 = [c ^ x for c in (w[p:] + w[:p])]
    order = []
    for c in w2[1:]:
        if c == 0:
            break
        if popcount(c) == 1:
            order.append(c.bit_length() - 1)
    new = {old: i for i, old in enumerate(order)}
    return [sum(1 << new[i] for i in range(n) if v >> i & 1) for v in w2]


def lag_normalise(w, n):
    pos, k = event_positions(w, n)
    L, P = len(w), 2 * k
    best = max((pos(x, r) * P - L * r, x, r) for x in range(1 << n)
               for r in range(-P, P) if (r - popcount(x)) % 2 == 0)
    _, x, r = best
    return rotate_translate_sort(w, n, pos(x, r) % len(w), x)


def last_normalise(w, n):
    pos, k = event_positions(w, n)
    x = max((v for v in range(1 << n) if popcount(v) % 2 == 0), key=lambda v: pos(v, 0))
    return rotate_translate_sort(w, n, pos(x, 0) % len(w), x)


def assignment(E, pos):
    val = {}
    for key, v in E.var.items():
        if key[0] == "lt":
            _, a, r, b, s = key
            val[v] = pos(a, r) < pos(b, s)
        elif key[0] == "nc":
            _, a, b, dl = key
            val[v] = len({pos(b, r + dl) < pos(a, r) for r in E.ranks(a)}) == 2
    return val


def violated(clauses, val):
    return [c for c in clauses if not any(val.get(abs(l)) == (l > 0) for l in c)]


def check_wr(n, w, norm, revlex=0):
    w2 = normalise(w, n) if norm == "shortest" else lag_normalise(w, n)
    assert represents_Qn(w2, n)[0]
    pos, k = event_positions(w2, n)
    E = WindowCNF(n, k, norm=norm).build(revlex=revlex)
    X = assignment(E, pos)
    if not revlex:
        return len(violated(E.clauses, X)), len(E.clauses)
    # reversed assignment: Y[rho(v)] = X[v]
    Y = {}
    for key, v in E.var.items():
        if key[0] == "lt":
            m = E.rho(key)
            Y[abs(m)] = X[v] if m > 0 else not X[v]
        elif key[0] == "nc":
            Y[v] = None
    # non-alternation auxiliaries of Y: recompute from Y's lt values
    for key, v in E.var.items():
        if key[0] == "nc":
            _, a, b, dl = key
            lits = [E.before(b, r + dl, a, r) for r in E.ranks(a)]
            vals = {Y[abs(l)] == (l > 0) for l in lits}
            Y[v] = len(vals) == 2
    best = None
    for Z in (X, Y):
        Z = dict(Z)
        # lex 'equal so far' auxiliaries: set them to the truth
        lexv = sorted(v for key, v in E.var.items() if key[0] == "lexeq")
        bad = violated([c for c in E.clauses if all(abs(l) not in lexv for l in c)], Z)
        # evaluate the lex constraint directly
        bad_lex = not lex_holds(E, Z, revlex)
        nb = len(bad) + int(bad_lex)
        best = nb if best is None else min(best, nb)
    return best, len(E.clauses)


def lex_holds(E, Z, m):
    X, Y = [], []
    for y in sorted(E.V, key=lambda v: (popcount(v), v)):
        for s in range(-1, 2):
            if y == 0 or (s - popcount(y)) % 2 or len(X) >= m:
                continue
            l = E.before(y, s, 0, 0)
            if isinstance(l, bool) or l is None:
                continue
            key = ("lt",) + next(k[1:] for k, v in E.var.items() if v == abs(l))
            X.append(Z[abs(l)])
            r = E.rho(key)
            Y.append(Z[abs(r)] == (r > 0))
    return X <= Y


def check_crr(n, w):
    w2 = last_normalise(w, n)
    assert represents_Qn(w2, n)[0]
    pos, k = event_positions(w2, n)
    R = CRR(n, k).build()
    val = {v: pos(a, r) < pos(b, r) for (r, a, b), v in R.var.items()}
    ids = sorted(set(range(1, R.nv + 1)) - set(R.var.values()))
    aux = []
    for a, b in itertools.combinations(range(1 << n), 2):
        if popcount(a ^ b) != 3:
            continue
        for wdw in range(2 * k):
            c, d = (a, b) if popcount(a) % 2 == wdw % 2 else (b, a)
            aux.append(pos(d, wdw + 1) < pos(c, wdw))
    assert len(ids) == len(aux)
    val.update(zip(ids, aux))
    return len(violated(R.clauses, val)), len(R.clauses)


def check_pfr(n, w, cls=PFR):
    w2 = last_normalise(w, n)
    assert represents_Qn(w2, n)[0]
    pos, k = event_positions(w2, n)
    R = cls(n, k).build()
    val = {v: pos(a, s) < pos(b, s) for key, v in R.var.items() if key[0] == "o"
           for (_, s, a, b) in [key]}
    # every auxiliary u occurs in binary implications u -> l and in one disjunction:
    # give it the value of the conjunction it stands for
    imp = {}
    for c in R.clauses:
        if len(c) == 2 and c[0] < 0 and -c[0] not in val:
            imp.setdefault(-c[0], []).append(c[1])
    for u, lits in imp.items():
        val[u] = all(val[abs(l)] == (l > 0) for l in lits)
    return len(violated(R.clauses, val)), len(R.clauses)


if __name__ == "__main__":
    args = sys.argv[1:]
    total = 0
    for i in range(0, len(args), 2):
        n, w = int(args[i]), list(map(int, open(args[i + 1]).read().split()))
        assert represents_Qn(w, n)[0], args[i + 1]
        res = {
            "WR shortest": check_wr(n, w, "shortest"),
            "WR shortest+revlex": check_wr(n, w, "shortest", revlex=60),
            "WR lag": check_wr(n, w, "lag"),
            "CRR": check_crr(n, w),
            "PFR": check_pfr(n, w),
            "PFR+": check_pfr(n, w, PFRP),
        }
        for name, (bad, tot) in res.items():
            total += bad
            print(f"{args[i + 1]} (Q_{n}): {name}: {bad} of {tot} clauses violated")
    print("OK" if total == 0 else f"FAILED: {total} violations")
    sys.exit(1 if total else 0)
