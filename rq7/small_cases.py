#!/usr/bin/env python3
"""
Reproduce the small values of R(Q_n) with the event model (event_cnf.py) and, as an
independent cross-check, with the plain "occurrence order" model (a linear order on all
k*2^n letter occurrences, full transitivity, no theory used).

Expected:  R(Q_2)=2, R(Q_3)=3, R(Q_4)=R(Q_5)=4, and Q_6 is 4-representable
(the Q_6 instance takes minutes; pass --q6 to include it).

Requires:  pip install python-sat
"""
import itertools
import sys
import time

from pysat.solvers import Cadical195

from event_cnf import EventCNF


def event_model(n, k, tri):
    E = EventCNF(n, k).build(tri)
    with Cadical195(bootstrap_with=E.clauses) as S:
        return S.solve()


def occurrence_model(n, k):
    """k-uniform representability of Q_n straight from the definition."""
    V = range(1 << n)
    occ = [(x, i) for x in V for i in range(k)]
    idx = {o: j for j, o in enumerate(occ)}
    var = {}
    def lt(o1, o2):
        a, b = idx[o1], idx[o2]
        if a < b:
            return var.setdefault((a, b), len(var) + 1)
        return -var.setdefault((b, a), len(var) + 1)
    cl = []
    for x in V:
        for i in range(k - 1):
            cl.append([lt((x, i), (x, i + 1))])
    N = len(occ)
    for a in range(N):
        for b in range(a + 1, N):
            for c in range(b + 1, N):
                ab, bc, ac = lt(occ[a], occ[b]), lt(occ[b], occ[c]), lt(occ[a], occ[c])
                cl.append([-ab, -bc, ac]); cl.append([ab, bc, -ac])
    for o in occ:
        if o != (0, 0):
            cl.append([lt((0, 0), o)])           # cyclic shift: the word starts with 0
    for x, y in itertools.combinations(V, 2):
        c = lt((x, 0), (y, 0))
        A = [lt((x, i), (y, i)) for i in range(k)] + [lt((y, i), (x, i + 1)) for i in range(k - 1)]
        B = [lt((y, i), (x, i)) for i in range(k)] + [lt((x, i), (y, i + 1)) for i in range(k - 1)]
        if bin(x ^ y).count("1") == 1:
            cl += [[-c, l] for l in A] + [[c, l] for l in B]
        else:
            cl.append([-c] + [-l for l in A]); cl.append([c] + [-l for l in B])
    with Cadical195(bootstrap_with=cl) as S:
        return S.solve()


if __name__ == "__main__":
    cases = [(2, 1), (2, 2), (3, 2), (3, 3), (4, 3), (4, 4), (5, 3), (5, 4)]
    if "--q6" in sys.argv:
        cases.append((6, 4))
    for n, k in cases:
        t = time.time()
        res = {tri: event_model(n, k, tri) for tri in ("none", "samerank", "all")}
        occ = occurrence_model(n, k) if n <= 5 else None
        verdict = "k-representable" if res["all"] else "NOT k-representable"
        print(f"Q_{n}, k={k}: event model (tri none/samerank/all) = "
              f"{['UNSAT', 'SAT'][res['none']]}/{['UNSAT', 'SAT'][res['samerank']]}/{['UNSAT', 'SAT'][res['all']]}; "
              f"occurrence model = {'-' if occ is None else ['UNSAT', 'SAT'][occ]}  -> {verdict}  ({time.time() - t:.1f}s)",
              flush=True)
        if occ is not None:
            assert occ == res["all"], "models disagree!"
