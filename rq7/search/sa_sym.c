/* Symmetric weighted local search for k-uniform word-representants of Q_n (sibling of sa.c).

   The word is kept invariant under  w[i + L/M] = g(w[i])  (indices mod L = k 2^n), where g is an automorphism
   of Q_n of order M.  A symmetry of a representant maps an event (v, r) to (g v, r + S) and acts on the word as a
   shift by L/M; faithfulness on ranks forces M | 2k and S = 2k/M (README section 6b).  The word is therefore a block
   B of length L/M followed by g(B), g^2(B), ..., g^(M-1)(B).  Parity forces |g v| = |v| + S (mod 2); for a pure
   translation g(v) = v xor a (M = 2, S = k) this means |a| = k (mod 2).

   Initial word: the parity height function h0(v) = |v| mod 2 is taken to the height function (h0 o g^-1) + S by a
   random saturated chain of firings (that chain is B).  Every edge alternates, and the symmetry holds, by construction.

   Moves are the moves of sa.c (a letter slides inside the window bounded by its neighbours), applied simultaneously to
   all M images of the chosen occurrence, so edges keep alternating and the symmetry is kept.  A move whose length is at
   least L/M is skipped so that the M images act on disjoint stretches.  The acceptance test uses the weighted change
   divided by M.  Like sa.c this can find representants, never refute them: a failure says nothing about words without
   the chosen symmetry.

   usage: sa_sym n k seed seconds T bumpevery pt outfile cycles mask
     cycles  coordinate permutation as cycles separated by '/', e.g. 01234/56, or '-' for the identity (n <= 10)
     mask    translation mask A (integer, bit i flips coordinate i); g(v) = p(v) xor A
   Build: cc -O3 -march=native -o sa_sym sa_sym.c -lm.  A solution is written to outfile and should be checked with
   check_word.py.  Exit status 0 means solved.

   Calibration (2026-09-30; every word reported as solved passed check_word.py, the Q8 ones also an independent checker):
     Q6, k=4, T=0.5, 40 s:  sa_sym 6 4 SEED 40 0.5 100000 100 out.txt - 3
                            translation of weight 2: 3 of 3 seeds solved, in 1.1M to 13M moves (plain sa: 2 of 3, in 33M to 53M).
                            "0123" with mask 0 (order 4) and mask 1 (order 8, the README's map): stall at 24 violations.
     Q8, k=5, T=0.8, 90 s:  sa_sym 8 5 SEED 90 0.8 100000 100 out.txt - MASK
                            MASK 7 (weight 3): 5 of 8 seeds solved, in 7.5M to 45M moves; plain sa solved 1 of 16 seeds in 600 s.
                            MASK 1, 31, 127 (weights 1, 5, 7): 0 of 8, lowest violations about 300, 2 and 15.
                            "01234" 0 (order 5): lowest 96 to 231.  Order 10 ("01234" 32, "01234/56" 128): lowest 266 to 686.
     Q7, k=4, T=0.5 and 0.8, 90 s:  MASK 3, 15, 63 (weights 2, 4, 6): 0 of 24 solved, lowest 80 to 122 violations
                            (plain sa, 4 runs: 71 to 101).  The wall at Q7, k=4 does not move under these symmetries.
   So only a well-chosen translation helped, and the helpful weight depended on (n, k). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <time.h>

static int n, k, N, L, M, Lb, S;
static int *gv, *ginv, **gpow;
static int *W, *oi, *occ;
static unsigned char *bad;
static int *wt, *blist, *bidx, nbad;
static long cost;
static uint64_t rng;
static inline uint64_t rnd(void) { rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17; return rng; }
static inline int adj(int x, int y) { return __builtin_popcount(x ^ y) == 1; }
static inline int md(int p) { p %= L; return p < 0 ? p + L : p; }
static inline int pid(int x, int y) { return x < y ? x * N + y : y * N + x; }

static int alternates(int x, int y) {
  int a[64], b[64], t = 0;
  for (int j = 0; j < k; j++) { a[t] = occ[x * k + j]; b[t++] = 0; }
  for (int j = 0; j < k; j++) { a[t] = occ[y * k + j]; b[t++] = 1; }
  for (int i = 1; i < t; i++) { int va = a[i], vb = b[i], j = i - 1; while (j >= 0 && a[j] > va) { a[j + 1] = a[j]; b[j + 1] = b[j]; j--; } a[j + 1] = va; b[j + 1] = vb; }
  for (int i = 0; i < t; i++) if (b[i] == b[(i + 1) % t]) return 0;
  return 1;
}
static void setbad(int id, int v) {
  if (bad[id] == v) return;
  bad[id] = v;
  if (v) { bidx[id] = nbad; blist[nbad++] = id; }
  else { int i = bidx[id], last = blist[--nbad]; blist[i] = last; bidx[last] = i; }
}
static void swap_pos(int p, int q) {
  int x = W[p], y = W[q], jx = oi[p], jy = oi[q];
  W[p] = y; W[q] = x; oi[p] = jy; oi[q] = jx; occ[x * k + jx] = q; occ[y * k + jy] = p;
}
static int crossed[4096], ncr, *stamp, curstamp = 0;
static int do_move(int p, int m) {
  ncr = 0; curstamp++;
  int dir = m < 0 ? -1 : 1, steps = m < 0 ? -m : m;
  for (int t = 0; t < steps; t++) { int a = md(p + dir * t), b = md(p + dir * (t + 1)); int z = W[b]; if (stamp[z] != curstamp) { stamp[z] = curstamp; crossed[ncr++] = z; } swap_pos(a, b); }
  return md(p + m);
}

static int is_symmetric(void) {
  for (int i = 0; i < L; i++) if (W[md(i + Lb)] != gv[W[i]]) return 0;
  return 1;
}

int main(int argc, char **argv) {
  if (argc < 11) { fprintf(stderr, "usage: sa_sym n k seed seconds T bumpevery pt outfile cycles mask\n"); return 2; }
  n = atoi(argv[1]); k = atoi(argv[2]); rng = strtoull(argv[3], 0, 10) * 2654435761ULL + 88172645463325252ULL;
  double secs = atof(argv[4]), T = atof(argv[5]); long bumpevery = atol(argv[6]); unsigned PT = atoi(argv[7]);
  const char *outf = argv[8], *cyc = argv[9]; unsigned A = strtoul(argv[10], 0, 0);
  N = 1 << n; L = k * N;

  /* the automorphism g(v) = p(v) xor A */
  int perm[16]; for (int c = 0; c < n; c++) perm[c] = c;
  if (strcmp(cyc, "-")) {
    int first = -1, prev = -1;
    for (const char *s = cyc; ; s++) {
      if (*s == '/' || *s == 0) { if (prev >= 0 && first >= 0 && prev != first) perm[prev] = first; first = prev = -1; if (!*s) break; continue; }
      int c = *s - '0'; if (c < 0 || c >= n) { fprintf(stderr, "bad cycle spec\n"); return 2; }
      if (first < 0) first = c; else perm[prev] = c;
      prev = c;
    }
  }
  gv = malloc(N * sizeof(int)); ginv = malloc(N * sizeof(int));
  for (int v = 0; v < N; v++) { int r = 0; for (int c = 0; c < n; c++) r |= ((v >> c) & 1) << perm[c]; gv[v] = r ^ (int)A; }
  for (int v = 0; v < N; v++) ginv[gv[v]] = v;
  /* order of g */
  M = 0; { int *cur = malloc(N * sizeof(int)); for (int v = 0; v < N; v++) cur[v] = v;
    for (int t = 1; t <= 4 * k + 2; t++) { int idn = 1; for (int v = 0; v < N; v++) { cur[v] = gv[cur[v]]; if (cur[v] != v) idn = 0; } if (idn) { M = t; break; } } free(cur); }
  if (!M) { fprintf(stderr, "g has order > 4k+2, not admissible\n"); return 2; }
  if ((2 * k) % M) { fprintf(stderr, "order M=%d does not divide 2k=%d: no faithful action on ranks\n", M, 2 * k); return 2; }
  S = 2 * k / M; Lb = L / M;
  for (int v = 0; v < N; v++) if ((__builtin_popcount(gv[v]) - __builtin_popcount(v) - S) & 1) { fprintf(stderr, "parity: |g v| != |v| + S (mod 2) for v=%d (S=%d)\n", v, S); return 2; }
  gpow = malloc(M * sizeof(int *)); gpow[0] = malloc(N * sizeof(int)); for (int v = 0; v < N; v++) gpow[0][v] = v;
  for (int t = 1; t < M; t++) { gpow[t] = malloc(N * sizeof(int)); for (int v = 0; v < N; v++) gpow[t][v] = gv[gpow[t - 1][v]]; }

  /* initial block: saturated chain from h0 = parity to (h0 o g^-1) + S */
  int *h = malloc(N * sizeof(int)), *need = malloc(N * sizeof(int)), *B = malloc(Lb * sizeof(int)); long tot = 0;
  for (int v = 0; v < N; v++) h[v] = __builtin_popcount(v) & 1;
  for (int v = 0; v < N; v++) { int tg = (__builtin_popcount(ginv[v]) & 1) + S - h[v]; if (tg < 0 || (tg & 1)) { fprintf(stderr, "target height not reachable at v=%d\n", v); return 2; } need[v] = tg / 2; tot += need[v]; }
  if (tot != Lb) { fprintf(stderr, "block length %ld != L/M=%d\n", tot, Lb); return 2; }
  for (int q = 0; q < Lb; q++) {
    int s0 = rnd() % N, pick = -1;
    for (int i = 0; i < N && pick < 0; i++) { int v = (s0 + i) % N; if (need[v] <= 0) continue; int ok = 1; for (int c = 0; c < n; c++) if (h[v ^ (1 << c)] != h[v] + 1) { ok = 0; break; } if (ok) pick = v; }
    if (pick < 0) { fprintf(stderr, "no eligible firing (internal error)\n"); return 2; }
    B[q] = pick; h[pick] += 2; need[pick]--;
  }
  W = malloc(L * sizeof(int)); oi = malloc(L * sizeof(int)); occ = malloc(N * k * sizeof(int));
  { int *cnt = calloc(N, sizeof(int));
    for (int p = 0; p < L; p++) { int t = p / Lb, o = p % Lb; int v = gpow[t][B[o]]; W[p] = v; oi[p] = cnt[v]; occ[v * k + cnt[v]] = p; cnt[v]++; }
    for (int v = 0; v < N; v++) if (cnt[v] != k) { fprintf(stderr, "letter %d occurs %d times, not k=%d (group/orbit mismatch)\n", v, cnt[v], k); return 2; }
    free(cnt); }
  if (!is_symmetric()) { fprintf(stderr, "initial word not symmetric (internal error)\n"); return 2; }

  bad = calloc(N * N, 1); wt = malloc(N * N * sizeof(int)); blist = malloc(N * N * sizeof(int)); bidx = malloc(N * N * sizeof(int)); stamp = calloc(N, sizeof(int));
  int *pst = calloc(N * N, sizeof(int)), curp = 0;
  for (int i = 0; i < N * N; i++) wt[i] = 1;
  nbad = 0; cost = 0;
  for (int x = 0; x < N; x++) for (int y = x + 1; y < N; y++) if (!adj(x, y)) { int b = alternates(x, y); setbad(x * N + y, b); cost += b; }
  fprintf(stderr, "M=%d S=%d L/M=%d initial bad %d\n", M, S, Lb, nbad);

  int bestbad = nbad; long mv = 0, lastimp = 0; clock_t c0 = clock();
  int **crt = malloc(M * sizeof(int *)); for (int t = 0; t < M; t++) crt[t] = malloc(N * sizeof(int));
  int *ncrt = malloc(M * sizeof(int)), *mover = malloc(M * sizeof(int)), *newpos = malloc(M * sizeof(int));
  int *chg_id = malloc(M * N * sizeof(int)); unsigned char *chg_st = malloc(M * N);
  while (1) {
    mv++;
    if ((mv & 0xfffff) == 0) {
      double el = (double)(clock() - c0) / CLOCKS_PER_SEC;
      if (el > secs) break;
      if ((mv & 0xffffff) == 0) fprintf(stderr, "t=%.0fs moves=%ld bad=%d best=%d wcost=%ld\n", el, mv, nbad, bestbad, cost);
    }
    if (bumpevery > 0 && mv - lastimp > bumpevery) { for (int i = 0; i < nbad; i++) { wt[blist[i]]++; cost++; } lastimp = mv; }
    int p0, x, target = -1;
    if (nbad > 0 && (rnd() % 1000) < PT) {
      int id = blist[rnd() % nbad]; int a = id / N, b = id % N;
      if (rnd() & 1) { int t = a; a = b; b = t; }
      x = a; target = b; p0 = occ[x * k + rnd() % k];
    } else { p0 = rnd() % L; x = W[p0]; }
    int lo = 0, hi = 0;
    while (-lo < L) { int q = md(p0 + lo - 1); if (adj(W[q], x) || W[q] == x) break; lo--; }
    while (hi < L) { int q = md(p0 + hi + 1); if (adj(W[q], x) || W[q] == x) break; hi++; }
    if (hi == lo) continue;
    int m = 0;
    if (target >= 0) {
      int mr = 0, ml = 0;
      for (int t = 1; t <= hi; t++) if (W[md(p0 + t)] == target) { mr = t; break; }
      for (int t = -1; t >= lo; t--) if (W[md(p0 + t)] == target) { ml = t; break; }
      if (mr && ml) m = (rnd() & 1) ? mr : ml; else m = mr ? mr : ml;
    }
    if (m == 0) { do { m = lo + (int)(rnd() % (uint64_t)(hi - lo + 1)); } while (m == 0); }
    if (abs(m) >= Lb) continue;
    for (int t = 0; t < M; t++) { int pos = md(p0 + t * Lb); mover[t] = W[pos]; newpos[t] = do_move(pos, m); ncrt[t] = ncr; memcpy(crt[t], crossed, ncr * sizeof(int)); }
    curp++; long d = 0; int nn = 0;
    for (int t = 0; t < M; t++) for (int i = 0; i < ncrt[t]; i++) {
      int z = crt[t][i], xt = mover[t], id = pid(xt, z);
      if (pst[id] == curp) continue; pst[id] = curp;
      int nb = adj(xt, z) ? 0 : alternates(xt, z);
      chg_id[nn] = id; chg_st[nn] = nb; nn++; d += (long)(nb - bad[id]) * wt[id];
    }
    double dm = (double)d / M;
    if (d <= 0 || (T > 0 && exp(-dm / T) * 4294967296.0 > (double)(rnd() & 0xffffffffULL))) {
      for (int j = 0; j < nn; j++) setbad(chg_id[j], chg_st[j]);
      cost += d;
      if (nbad < bestbad) { bestbad = nbad; lastimp = mv; if (bestbad <= 10) fprintf(stderr, "t=%.1fs moves=%ld best=%d\n", (double)(clock() - c0) / CLOCKS_PER_SEC, mv, bestbad); }
      if (nbad == 0) break;
    } else for (int t = 0; t < M; t++) do_move(newpos[t], -m);
  }
  fprintf(stderr, "end: bad %d best %d moves %ld symmetric=%d\n", nbad, bestbad, mv, is_symmetric());
  { int hist[32] = {0}; for (int i = 0; i < nbad; i++) { int id = blist[i]; hist[__builtin_popcount((id / N) ^ (id % N))]++; }
    fprintf(stderr, "bad pairs by distance:"); for (int d = 2; d <= n; d++) fprintf(stderr, " d%d:%d", d, hist[d]); fprintf(stderr, "\n"); }
  if (nbad == 0) { FILE *f = fopen(outf, "w"); for (int i = 0; i < L; i++) fprintf(f, "%d ", W[i]); fprintf(f, "\n"); fclose(f); printf("FOUND\n"); return 0; }
  return 1;
}
