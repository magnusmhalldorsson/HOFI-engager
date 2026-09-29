#!/usr/bin/env python3
"""
Soundness test for event_cnf.py: every clause must be satisfied by every genuine,
normalised representation.

For a word w that represents Q_n (checked directly from the definition), this script
  1. picks a globally shortest arc and normalises w exactly as in the proof
     (rotate, translate by the arc's letter, permute coordinates);
  2. builds the height function and the event order of the normalised word
     (Lemma 2 of README.md), asserting the potential exists (the square lemma at work);
  3. assigns every CNF variable its truth value in that event order, and
  4. checks that all clauses of event_cnf.py (all three --tri variants) are satisfied.

Usage: python3 soundness_test.py N WORDFILE      (WORDFILE: letters 0..2^N-1, whitespace separated)
"""
import sys
from collections import defaultdict, deque

from check_word import represents_Qn
from event_cnf import EventCNF, popcount


def normalise(w, n):
    L = len(w)
    pos = defaultdict(list)
    for i, c in enumerate(w):
        pos[c].append(i)
    best = None
    for v, P in pos.items():
        for j in range(len(P)):
            s, e = P[j], P[(j + 1) % len(P)]
            length = (e - s) % L - 1
            if best is None or length < best[0]:
                best = (length, v, s)
    _, a, s = best
    w2 = [c ^ a for c in (w[s:] + w[:s])]            # rotate, then translate by a
    order = []
    for c in w2[1:]:
        if c == 0:
            break
        if popcount(c) == 1:
            order.append(c.bit_length() - 1)
    new = {old: i for i, old in enumerate(order)}      # coordinate old -> new position
    def perm(v):
        return sum(1 << new[i] for i in range(n) if v >> i & 1)
    return [perm(c) for c in w2]


def event_positions(w, n):
    """rank function of the (normalised) word read from its start: returns pos(v, r)"""
    L = len(w)
    k = w.count(0)
    first = {}
    for i, c in enumerate(w):
        first.setdefault(c, i)
    h = {0: 0}
    q = deque([0])
    while q:
        a = q.popleft()
        for i in range(n):
            b = a ^ (1 << i)
            want = h[a] + (1 if first[a] < first[b] else -1)
            if b in h:
                assert h[b] == want, "no height function: square lemma violated?!"
            else:
                h[b] = want
                q.append(b)
    at = {}
    cur = dict(h)
    for i, c in enumerate(w):
        # every neighbour must be one higher at the moment c occurs (Lemma 2(c))
        assert all(cur[c ^ (1 << j)] == cur[c] + 1 for j in range(n))
        at[(c, cur[c])] = i
        cur[c] += 2
    P = 2 * k
    def pos(v, r):
        m, rem = divmod(r - h[v], P)
        return at[(v, h[v] + rem)] + m * L
    return pos, k


def check(n, w):
    ok, msg = represents_Qn(w, n)
    assert ok, msg
    w = normalise(w, n)
    assert represents_Qn(w, n)[0]
    pos, k = event_positions(w, n)
    results = {}
    for tri in ("none", "samerank", "all"):
        if tri == "all" and n > 6:
            continue
        E = EventCNF(n, k).build(tri)
        val = {}
        for key, v in E.var.items():
            if key[0] == "lt":
                _, a, r, b, s = key
                val[v] = pos(a, r) < pos(b, s)
            else:
                _, a, b, dl = key
                pat = {pos(b, r + dl) < pos(a, r) for r in E.ranks(a)}
                val[v] = len(pat) == 2
        bad = sum(1 for c in E.clauses if not any(val[abs(l)] == (l > 0) for l in c))
        results[tri] = (bad, len(E.clauses))
    return k, results


if __name__ == "__main__":
    n = int(sys.argv[1])
    w = list(map(int, open(sys.argv[2]).read().split()))
    k, res = check(n, w)
    for tri, (bad, tot) in res.items():
        print(f"Q_{n}, k={k}, tri={tri}: {bad} of {tot} clauses violated")
    sys.exit(1 if any(b for b, _ in res.values()) else 0)
