/* lratx: parse a (possibly truncated) binary LRAT proof produced for a CNF with m_input clauses.
   - checks that all hints are positive (no RAT steps),
   - writes the longest prefix of complete records to TRUNC,
   - writes to KOUT all clauses alive at the end of that prefix whose id is > m_orig
     (i.e. derived clauses and inherited lemmas of the input), keeping those with <= lmax literals.
   usage: lratx proof.lrat input.cnf m_orig lmax trunc.lrat kout.cnf nvars
   Input clauses with id in (m_orig, m_input] are read from input.cnf (they are inherited lemmas). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

static unsigned char *buf; static size_t n;
static int getv(size_t *i, uint64_t *x) {
  uint64_t v = 0; int sh = 0;
  while (1) {
    if (*i >= n) return 0;
    unsigned c = buf[(*i)++];
    v |= (uint64_t)(c & 0x7f) << sh; sh += 7;
    if (c < 0x80) break;
  }
  *x = v; return 1;
}
typedef struct { int *lits; int len; } cl;
static cl *C; static size_t cap = 0; static unsigned char *alive;
static void ensure(size_t id) {
  if (id < cap) return;
  size_t nc = cap ? cap : 1 << 20;
  while (nc <= id) nc *= 2;
  C = realloc(C, nc * sizeof(cl)); alive = realloc(alive, nc);
  memset(C + cap, 0, (nc - cap) * sizeof(cl)); memset(alive + cap, 0, nc - cap);
  cap = nc;
}
int main(int argc, char **argv) {
  if (argc != 8) { fprintf(stderr, "usage\n"); return 1; }
  const char *pf = argv[1], *cf = argv[2]; size_t morig = atol(argv[3]); int lmax = atoi(argv[4]);
  const char *tf = argv[5], *kf = argv[6]; long nv = atol(argv[7]);
  /* read input CNF clauses (only ids > morig are needed) */
  FILE *f = fopen(cf, "r"); if (!f) return 1;
  char line[1 << 16]; size_t id = 0; int tmp[4096];
  while (fgets(line, sizeof line, f)) {
    if (line[0] == 'c' || line[0] == 'p') continue;
    id++;
    if (id <= morig) continue;
    int len = 0; char *p = line; int v;
    while (sscanf(p, "%d", &v) == 1) {
      if (v == 0) break;
      tmp[len++] = v;
      while (*p == ' ') p++;
      while (*p && *p != ' ') p++;
    }
    ensure(id); C[id].len = len; C[id].lits = malloc(len * sizeof(int)); memcpy(C[id].lits, tmp, len * sizeof(int)); alive[id] = 1;
  }
  size_t minput = id; fclose(f);
  /* read proof */
  f = fopen(pf, "rb"); fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
  buf = malloc(n ? n : 1); if (fread(buf, 1, n, f) != n) return 1; fclose(f);
  size_t i = 0, ok = 0; long nadd = 0, ndel = 0; int *lits = malloc(1 << 20);
  while (i < n) {
    size_t j = i; unsigned t = buf[j++]; uint64_t x;
    if (t == 'a') {
      if (!getv(&j, &x)) break; size_t cid = x >> 1;
      int len = 0; int complete = 0;
      while (getv(&j, &x)) { if (x == 0) { complete = 1; break; } lits[len++] = (x & 1) ? -(int)(x >> 1) : (int)(x >> 1); }
      if (!complete) break;
      complete = 0;
      while (getv(&j, &x)) { if (x == 0) { complete = 1; break; } if (x & 1) { fprintf(stderr, "RAT hint in %zu\n", cid); return 3; } }
      if (!complete) break;
      ensure(cid); free(C[cid].lits);
      C[cid].len = len; C[cid].lits = malloc(len * sizeof(int) + 1); memcpy(C[cid].lits, lits, len * sizeof(int)); alive[cid] = 1; nadd++;
    } else if (t == 'd') {
      int complete = 0; size_t cnt = 0; size_t start = j;
      while (getv(&j, &x)) { if (x == 0) { complete = 1; break; } cnt++; }
      if (!complete) break;
      size_t k = start;
      while (1) { getv(&k, &x); if (x == 0) break; size_t d = x >> 1; if (d < cap && alive[d]) { alive[d] = 0; free(C[d].lits); C[d].lits = NULL; } ndel++; }
    } else { fprintf(stderr, "bad tag %u at %zu\n", t, i); return 4; }
    i = j; ok = i;
  }
  f = fopen(tf, "wb"); fwrite(buf, 1, ok, f); fclose(f);
  long nk = 0;
  for (size_t c = morig + 1; c < cap; c++) if (alive[c] && C[c].len <= lmax) nk++;
  f = fopen(kf, "w"); fprintf(f, "p cnf %ld %ld\n", nv, nk);
  for (size_t c = morig + 1; c < cap; c++) if (alive[c] && C[c].len <= lmax) {
    for (int q = 0; q < C[c].len; q++) fprintf(f, "%d ", C[c].lits[q]);
    fprintf(f, "0\n");
  }
  fclose(f);
  printf("valid %zu of %zu bytes; added %ld; deletion ids %ld; input clauses %zu; kept %ld\n", ok, n, nadd, ndel, minput, nk);
  return 0;
}
