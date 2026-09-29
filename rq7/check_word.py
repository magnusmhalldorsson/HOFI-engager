#!/usr/bin/env python3
"""Check, straight from the definition, whether a word represents the hypercube Q_n:
letters x != y must alternate exactly when their binary labels differ in one bit.

Usage: python3 check_word.py N WORDFILE
"""
import sys


def represents_Qn(word, n):
    N = 1 << n
    occ = [[] for _ in range(N)]
    for i, c in enumerate(word):
        if not 0 <= c < N:
            return False, f"letter {c} out of range"
        occ[c].append(i)
    k = len(occ[0])
    if any(len(o) != k for o in occ):
        return False, "not uniform"
    for x in range(N):
        for y in range(x + 1, N):
            merged = sorted([(p, 0) for p in occ[x]] + [(p, 1) for p in occ[y]])
            alternate = all(merged[i][1] != merged[i + 1][1] for i in range(len(merged) - 1))
            if alternate != (bin(x ^ y).count("1") == 1):
                return False, f"pair {x},{y}: alternate={alternate}"
    return True, f"{k}-uniform word of length {len(word)} represents Q_{n}"


if __name__ == "__main__":
    n = int(sys.argv[1])
    w = list(map(int, open(sys.argv[2]).read().split()))
    ok, msg = represents_Qn(w, n)
    print(msg)
    sys.exit(0 if ok else 1)
