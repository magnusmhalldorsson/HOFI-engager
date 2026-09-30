#!/usr/bin/env python3
"""
Soundness test for antipodal_cases.py.  For a genuine representant w of Q_n (n odd):
compute M = max antipodal lag, normalise w as prescribed for its case, and check that every
clause of that case's CNF is satisfied.

Usage: python3 case_split_test.py N WORDFILE
"""
import sys

from antipodal_cases import build
from check_word import represents_Qn
from event_cnf import popcount
from soundness_test import event_positions, normalise


def max_lag_event(w, n):
    """(M, position, vertex) of a maximiser (x, r) of the antipodal lag with A_x(r+2) = M - 2
    (one exists unless M is attained by a constant pattern, which non-alternation forbids)."""
    pos, k = event_positions(w, n)
    full = (1 << n) - 1
    L = len(w)
    def lag(x, r):
        g = sum(1 for s in range(r - (n - 2), r + n - 1, 2) if pos(x ^ full, s) < pos(x, r))
        return 2 * g - (n - 2)
    events = []
    for x in range(1 << n):
        for r in range(-2 * k, 4 * k):
            if (r - popcount(x)) % 2 == 0 and 0 <= pos(x, r) < L:
                events.append((pos(x, r), x, r))
    M = max(lag(x, r) for _, x, r in events)
    for p, x, r in sorted(events):
        if lag(x, r) == M and lag(x, r + 2) == M - 2:
            return M, p, x
    raise AssertionError("no maximiser followed by a drop -- impossible for a representant")


def normalise_to_event(w, n, p, x):
    """rotate so the word starts at position p (an occurrence of x), translate by x, sort coordinates"""
    w2 = [c ^ x for c in (w[p:] + w[:p])]
    order = []
    for c in w2[1:]:
        if c == 0:
            break
        if popcount(c) == 1:
            order.append(c.bit_length() - 1)
    new = {old: i for i, old in enumerate(order)}
    return [sum(1 << new[i] for i in range(n) if v >> i & 1) for v in w2]


def check(n, w):
    assert represents_Qn(w, n)[0]
    M, p, x = max_lag_event(w, n)
    case = {3: "I", 5: "II", 7: "III"}[M]
    w2 = normalise(w, n) if case == "I" else normalise_to_event(w, n, p, x)
    assert represents_Qn(w2, n)[0]
    pos, k = event_positions(w2, n)
    E = build(n, k, case)
    val = {}
    for key, v in E.var.items():
        if key[0] == "lt":
            _, a, r, b, s = key
            val[v] = pos(a, r) < pos(b, s)
        else:
            _, a, b, dl = key
            val[v] = len({pos(b, r + dl) < pos(a, r) for r in E.ranks(a)}) == 2
    bad = sum(1 for c in E.clauses if not any(val[abs(l)] == (l > 0) for l in c))
    return M, case, bad, len(E.clauses)


if __name__ == "__main__":
    n = int(sys.argv[1])
    w = list(map(int, open(sys.argv[2]).read().split()))
    M, case, bad, tot = check(n, w)
    print(f"Q_{n}: max antipodal lag M={M} (case {case}): {bad} of {tot} clauses violated")
    sys.exit(1 if bad else 0)
