"""Flip-dynamics view of a k-uniform word representing Q_n (pure python).
State: height function h on Q_n (|h(x)-h(y)|=1 on edges, h(x) = |x| mod 2).  A letter occurrence x is a
'firing': x must be a local minimum (all neighbours at h(x)+1), and then h(x) += 2.
"""
import sys

def load(path):
    return list(map(int, open(path).read().split()))

def initial_height(word, n):
    """h(y)-h(x) = +1 iff x's first occurrence precedes y's (canonical orientation), h(0)=0."""
    N = 1 << n
    first = {}
    for i, c in enumerate(word):
        first.setdefault(c, i)
    h = [None] * N; h[0] = 0; stack = [0]
    while stack:
        x = stack.pop()
        for i in range(n):
            y = x ^ (1 << i)
            if h[y] is None:
                h[y] = h[x] + (1 if first[x] < first[y] else -1)
                stack.append(y)
    for x in range(N):
        for i in range(n):
            y = x ^ (1 << i)
            assert abs(h[x] - h[y]) == 1 and ((h[y] - h[x] == 1) == (first[x] < first[y]))
    return h

def simulate(word, n, record=None):
    """Replay the word, asserting every firing is at a local minimum; call record(t, x, h) before each firing."""
    N = 1 << n
    h = initial_height(word, n); h0 = h[:]
    for t, x in enumerate(word):
        for i in range(n):
            assert h[x ^ (1 << i)] == h[x] + 1, f"firing {x} at t={t} is not a local minimum"
        if record is not None:
            record(t, x, h)
        h[x] += 2
    k = len(word) // N
    assert all(h[v] - h0[v] == 2 * k for v in range(N)), "after one period every height must rise by 2k"
    return h0

if __name__ == "__main__":
    n = int(sys.argv[1]); w = load(sys.argv[2])
    h0 = simulate(w, n)
    src = sum(all(h0[x ^ (1 << i)] == h0[x] + 1 for i in range(n)) for x in range(1 << n))
    print(f"n={n} len={len(w)}: flip dynamics consistent; h0 range [{min(h0)},{max(h0)}]; #sources in h0 = {src}")
