import sys, glob
from flip import load
from rounds import rounds
from wrmodel import WR
n = int(sys.argv[1]); k_expected = int(sys.argv[2])
bad = 0; tot = 0
for f in sorted(glob.glob(sys.argv[3]))[:int(sys.argv[4])]:
    w = load(f); k, alpha = rounds(n, w); assert k == k_expected
    W = WR(n, k)
    res = W.evaluate([alpha[r] for r in range(2 * k)], True)
    tot += 1
    if res != (0, 0): bad += 1; print("  nonzero:", f.split('/')[-1], res)
print(f"n={n} k={k}: {tot} real representants, evaluator flags {bad} of them (must be 0)")
