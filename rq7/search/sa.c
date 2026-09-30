/* Weighted local search (simulated annealing + breakout weights) for k-uniform word-representants
   of Q_n.  Invariant: every edge pair alternates (a letter only moves within the window bounded by
   the nearest occurrences of its graph-neighbours).  Objective: weighted number of non-adjacent
   alternating pairs.  Heuristic only: it can find representants, never refute them.

   usage: sa n k seed seconds T bumpevery pt outfile [subset|-] [distmask] [diffset]
     T          annealing temperature (e.g. 0.3)
     bumpevery  moves without improvement before the weights of bad pairs are raised
     pt         per-mille of moves that target a random bad pair
     subset     file of vertices (induced subgraph); "-" for all of Q_n
     distmask   bit d set <=> pairs at distance d are required not to alternate (default all)
     diffset    file of difference vectors x^y of the pairs that are constrained
   A solution is written to outfile and should be checked with check_word.py. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <time.h>

static int n, k, N, L, NV; static int *verts, *inS; static unsigned distmask = ~0u; static unsigned char *dset;
static int *W, *oi, *occ;
static unsigned char *bad;
static int *wt;                 /* pair weights */
static int *blist, *bidx, nbad; /* list of bad pairs (encoded x*N+y, x<y) */
static long cost;               /* weighted */
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
static int crossed[8192], ncr, *stamp, curstamp = 0;
static int do_move(int p, int m) {
  ncr = 0; curstamp++;
  int dir = m < 0 ? -1 : 1, steps = m < 0 ? -m : m;
  for (int t = 0; t < steps; t++) { int a = md(p + dir * t), b = md(p + dir * (t + 1)); int z = W[b]; if (stamp[z] != curstamp) { stamp[z] = curstamp; crossed[ncr++] = z; } swap_pos(a, b); }
  return md(p + m);
}
int main(int argc, char **argv) {
  n = atoi(argv[1]); k = atoi(argv[2]); rng = strtoull(argv[3], 0, 10) * 2654435761ULL + 88172645463325252ULL;
  double secs = atof(argv[4]), T = atof(argv[5]); long bumpevery = atol(argv[6]); unsigned PT = atoi(argv[7]);
  const char *outf = argv[8];
  N = 1 << n;
  inS = calloc(N, sizeof(int)); verts = malloc(N * sizeof(int)); NV = 0;
  if (argc > 9 && strcmp(argv[9], "-")) { FILE *sf = fopen(argv[9], "r"); int v; while (fscanf(sf, "%d", &v) == 1) inS[v] = 1; fclose(sf); }
  else for (int v = 0; v < N; v++) inS[v] = 1;
  for (int v = 0; v < N; v++) if (inS[v]) verts[NV++] = v;
  if (argc > 10) distmask = strtoul(argv[10], 0, 0);
  dset = malloc(N); memset(dset, 1, N);
  if (argc > 11) { memset(dset, 0, N); FILE *df = fopen(argv[11], "r"); int v; while (fscanf(df, "%d", &v) == 1) dset[v] = 1; fclose(df); }
  L = k * NV;
  W = malloc(L * sizeof(int)); oi = malloc(L * sizeof(int)); occ = malloc(N * k * sizeof(int));
  bad = calloc(N * N, 1); wt = malloc(N * N * sizeof(int)); blist = malloc(N * N * sizeof(int)); bidx = malloc(N * N * sizeof(int)); stamp = calloc(N, sizeof(int));
  for (int i = 0; i < N * N; i++) wt[i] = 1;
  int p = 0;
  for (int j = 0; j < k; j++) for (int par = 0; par < 2; par++) for (int x = 0; x < N; x++) if (inS[x] && __builtin_popcount(x) % 2 == par) { W[p] = x; oi[p] = j; occ[x * k + j] = p; p++; }
  nbad = 0; cost = 0;
  for (int x = 0; x < N; x++) for (int y = x + 1; y < N; y++) if (inS[x] && inS[y] && !adj(x, y) && (distmask >> __builtin_popcount(x ^ y) & 1) && dset[x ^ y]) { int b = alternates(x, y); setbad(x * N + y, b); cost += b; }
  fprintf(stderr, "initial bad %d\n", nbad);
  unsigned char newst[8192]; int bestbad = nbad; long mv = 0, lastimp = 0;
  clock_t c0 = clock();
  while (1) {
    mv++;
    if ((mv & 0xfffff) == 0) {
      double el = (double)(clock() - c0) / CLOCKS_PER_SEC;
      if (el > secs) break;
      if ((mv & 0xffffff) == 0) fprintf(stderr, "t=%.0fs moves=%ld bad=%d best=%d wcost=%ld\n", el, mv, nbad, bestbad, cost);
    }
    if (bumpevery > 0 && mv - lastimp > bumpevery) {   /* breakout: raise weights of bad pairs */
      for (int i = 0; i < nbad; i++) { wt[blist[i]]++; cost++; }
      lastimp = mv;
    }
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
    int np = do_move(p0, m);
    long d = 0;
    for (int i = 0; i < ncr; i++) { int z = crossed[i]; int id = pid(x, z); int nb = (adj(x, z) || !(distmask >> __builtin_popcount(x ^ z) & 1) || !dset[x ^ z]) ? 0 : alternates(x, z); newst[i] = nb; d += (long)(nb - bad[id]) * wt[id]; }
    if (d <= 0 || (T > 0 && exp(-d / T) * 4294967296.0 > (double)(rnd() & 0xffffffffULL))) {
      for (int i = 0; i < ncr; i++) { int z = crossed[i]; setbad(pid(x, z), newst[i]); }
      cost += d;
      if (nbad < bestbad) { bestbad = nbad; lastimp = mv; if (bestbad <= 10) fprintf(stderr, "t=%.1fs moves=%ld best=%d\n", (double)(clock() - c0) / CLOCKS_PER_SEC, mv, bestbad); }
      if (nbad == 0) break;
    } else do_move(np, -m);
  }
  fprintf(stderr, "end: bad %d best %d moves %ld\n", nbad, bestbad, mv);
  { int hist[32] = {0}; for (int i = 0; i < nbad; i++) { int id = blist[i]; hist[__builtin_popcount((id / N) ^ (id % N))]++; }
    fprintf(stderr, "bad pairs by distance:"); for (int d = 2; d <= n; d++) fprintf(stderr, " d%d:%d", d, hist[d]); fprintf(stderr, "\n"); }
  if (nbad == 0) { FILE *f = fopen(outf, "w"); for (int i = 0; i < L; i++) fprintf(f, "%d ", W[i]); fprintf(f, "\n"); fclose(f); printf("FOUND\n"); return 0; }
  return 1;
}
