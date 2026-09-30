import sys, random, math
from wrmodel import WR, popcount
n, k, seed, iters = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
T0 = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
random.seed(seed)
W = WR(n, k); N = 1 << n
R = 2 * k
u = [[random.randint(0, 1) for _ in range(n)] for _ in range(R)]
c = [[random.uniform(0.5, 1.5) for _ in range(n)] for _ in range(R)]
def build(r):
    par = r % 2
    key = lambda v: sum(c[r][i] * (((v >> i) & 1) ^ u[r][i]) for i in range(n))
    return sorted(W.cls[par], key=key)
alphas = [build(r) for r in range(R)]
cur = W.evaluate(alphas); best = cur
for it in range(iters):
    r = random.randrange(R)
    old = (u[r][:], c[r][:], alphas[r])
    if random.random() < 0.3: u[r][random.randrange(n)] ^= 1
    else:
        i = random.randrange(n); c[r][i] = max(0.05, c[r][i] * math.exp(random.gauss(0, 0.5)))
    alphas[r] = build(r)
    new = W.evaluate(alphas)
    T = T0 * (1 - it / iters) + 0.05
    if new <= cur or random.random() < math.exp(-(new - cur) / T):
        cur = new
        if cur < best:
            best = cur
            if best == 0: break
    else:
        u[r], c[r], alphas[r] = old
    if it % 500 == 0: print(f"it {it} cur {cur} best {best}", flush=True)
print(f"n={n} k={k} seed={seed}: final best uncovered (d2+d3) = {best}; detail {W.evaluate(alphas, True)}")
