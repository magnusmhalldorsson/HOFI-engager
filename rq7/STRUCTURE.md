# Structure of uniform representants of Q_n

Working note, 2026-09-30. Labels: **(proved)** is a short argument given here. **(checked)** means
verified by computer on the witnesses `witnesses/q4_k4.txt` to `q10_k7.txt` with zero exceptions
(`lab/identities.py`, `lab/profiles.py`). **(observed)** means statistics of words found by search,
not a theorem.

Nothing here proves R(Q_7) >= 5 or R(Q_8) = 5. Section 4 says why the obvious counting routes are
slack, and section 5 says where an argument would have to live.

## 1. Words are flip sequences

Let w be a k-uniform cyclic word representing Q_n and h its height function (README section 3). Read
w from a cut. Each occurrence of a letter x is a *firing*: x can fire only when h(x) is a local
minimum (all n neighbors at h(x)+1), and then h(x) rises by 2.

**Lemma 1 (proved).** The k-uniform cyclic words on V(Q_n) in which every edge alternates are exactly
the saturated chains from h to h+2k in the lattice of height functions with h(x) = |x| mod 2. (The
pointwise maximum of two height functions is a height function, and a firing is a cover relation.
Every maximal chain fires each vertex exactly k times, and neighbors alternate because a firing
needs the neighbors above.)

For a pair x, y at distance d put D(t) = h_t(x) - h_t(y). The light cone keeps D in [-d, d]. D rises
by 2 when x fires and falls by 2 when y fires, and it is periodic. **x and y alternate iff D takes
exactly two adjacent values.** The word is a linear extension of the causal poset of firings, and
the representation problem asks for one extension in which every non-adjacent pair fails to
alternate.

## 2. Exact identities

**Lemma 2 (flow; proved, checked).** D is a closed walk on {-d, -d+2, ..., d}. Call the step between
D and D+2 a *level*. Each level is crossed upward exactly as often as downward; write u_j for this
number on level j, so the u_j sum to k. The support of (u_j) is an interval of levels, and
non-alternation holds iff the support has at least two levels.

At a firing of x put lambda = h(y) - h(x). Crossing level (D, D+2) contributes lambda = -D when x
fires and lambda = D+2 when y fires. Hence:

1. For every pair, the 2k values of lambda are symmetric about 1. In particular the mean is 1.
2. d = 2: exactly k of the 2k firings have lambda = 2 and the other k have lambda = 0.
3. d = 3: #(lambda = 3) = #(lambda = -1) = c = u_1 + u_3, and #(lambda = 1) = 2 u_2. The pair is
   non-alternating iff u_2 >= 1 and c >= 1. So 1 <= c <= k-1.
4. An *anticone* (x fires while y, at distance 3, is exactly one below) is always followed by a
   *cone* (the next firing of y, at which x is three above), because x cannot climb above h(y)+3.
   This is the README's inversion (x, r) < (y, r-1).

**Lemma 3 (rounds; proved, checked).** Let S be a set of vertices pairwise at distance 2. Examples:
the neighborhood N(u), or the four vertices of one parity class of a Q_3. Their heights stay inside a
band {rho, rho+2}, and only bottom vertices can fire, so the word restricted to S is a concatenation
of k permutations (rounds). In each round the first firing sees every other member level
(lambda = 0) and the last sees every other member above (lambda = 2).

Consequences. At a firing of x let G_x be the graph on the n coordinate directions in which ij is an
edge iff lambda(x + e_i + e_j) = 2.

* Averaged over all firings, |E(G_x)| = C(n,2)/2 and the numbers of triangles and of independent
  triples are both C(n,3)/4, exactly.
* A vertex y = x + e_T at distance 3 has lambda = 3 only if T is a triangle of G_x (x is the last of
  its round in its Q_3 class), and lambda = -1 only if T is an independent triple (x is first).
* So a Q_3 has at most one cone per class-round, at most 2k cones in all, and at least 4 (one per
  diagonal).

**Lemma 4 (cone windows; proved).** The diagonal {c, d} of a Q_3 C is covered in window w iff c is the
last of the parity-w class of C in round w, d is the first of the other class of C in round w+1
(so they are antipodal), and d's rank-(w+1) firing precedes c's rank-w firing. Only one diagonal of C
can be covered per window. The README's PFR+ is this condition, together with the distance-2 pair
orders.

## 3. What the found words look like (observed)

Required: every distance-3 pair needs a cone, so cones are at least 2^(n-1) C(n,3). Available
cone slots are the round-last firings, k 2^n C(n,3)/4 of them. So **at least a fraction 2/k of all
round-lasts must be cones**.

| n | k | cones per distance-3 pair | cone fraction of round-lasts | required 2/k |
|---|---|---|---|---|
| 4 | 4 | 1.250 | 0.625 | 0.500 |
| 5 | 4 | 1.181 | 0.591 | 0.500 |
| 6 | 4 | 1.189 | 0.595 | 0.500 |
| 7 | 5 | 1.566 | 0.626 | 0.400 |
| 8 | 5 | 1.622 | 0.649 | 0.400 |
| 9 | 6 | 1.824 | 0.608 | 0.333 |
| 10 | 7 | 2.014 | 0.575 | 0.286 |

At k = 4 the cone count per pair is only 1.2, barely above the minimum 1. The observed fraction is
about 0.6 at every k, so the requirement 2/k is tightest for small k, but at k = 4 it is still below
what the found words achieve.

Sampling 60 words each for Q_4 and Q_5 and 11 for Q_6 at k = 4: every Q_3 covers all four diagonals
(a check of the cone computation), the number of cone windows per Q_3 ranges from 4 to 8 with means
4.8 (Q_4), 5.05 (Q_5) and 5.3 (Q_6), and the cyclic cone patterns are varied (`lab/cones.py`). The fraction of Q_3's that are
cones in one window ranges over 0.0 to 1.0 in Q_4, 0.23 to 0.88 in Q_5 and 0.46 to 0.80 in Q_6. There
is no rigidity at Q_4 that one could propagate upward.

## 4. What does not work

* **Counting.** The required cone rate per firing, C(n,3)/(2k), equals the triangle count of a
  random graph G(n,1/2) exactly when k = 4, which looks tight. It is not: G need not be random, and
  Kruskal-Katona allows (asymptotically) about 2.8 times the requirement at the exact edge density
  C(n,2)/2. Goodman's lower bound on monochromatic triangles does not contradict it either. The
  required 4 of 2k = 8 cone slots per Q_3 is 50%, against about 60% observed.
* **Published counting bound.** Hefty-Horn-Muir-Owens Corollary 20 bounds R(G) below by
  log|N_X| / log(2e|X|). In Q_n two vertices at distance 2 have exactly two common neighbors, so
  |N_X| = O(|X|^2) and the bound is about 2. Their Theorem 25 needs a balanced bipartite graph whose
  bipartite complement is k-regular and C_4-free. The bipartite complement of Q_n has degree
  2^(n-1) - n and contains C_4's, so it does not apply.
* **Threshold rounds.** If every round is ordered by a weighted distance from a center (a linear
  functional), the exact distance-2/3 conditions fail even for Q_4 at k = 4: six long runs of
  `lab/threshold_search.py` stall at 5 to 6 uncovered distance-3 pairs. Found words are only
  moderately centered (Spearman correlation 0.4 to 0.75 between position in a round and distance to
  the best center). So a clean "ball-shaped rounds" construction cannot exist.

## 5. Where an argument would have to live

Everything above is satisfied with slack by the Q_6 witnesses, so a proof that Q_7 (or Q_8) is not
4-representable cannot come from these counts. The diversity requirement (all four diagonals of every
Q_3 covered, in windows coupled through shared rounds) is the crux, and it is exactly what PFR+
encodes. PFR+ restricted to Hamming balls up to radius 4 is satisfiable for (8,4) and (9,4), and
Kissat 4.0.4 has not decided the full formulas (PFR+(8,4) and WR(8,4) about 3 hours each, PFR+(9,4) about 2 hours, PFR+(7,4) 3 hours for comparison). A human proof would have to use a global
feature (antipodal pairs, as in README section 6) or settle the diversity problem by a new
design-theoretic argument.

Heuristic evidence on the annealer (`search/sa.c`, best violations; "d2+d3" means only distances 2 and 3
are required not to alternate):

| k | instance | result |
|---|---|---|
| 4 | Q_7 | 72-92 (d2+d3: 27-37) |
| 4 | Q_8 | 703-750 (d2+d3: 276-337) |
| 4 | Q_9 | 3251-3641 (d2+d3: 1261-1425) |
| 5 | Q_8 | solved, 1 of 16 seeds (372M moves) |
| 5 | Q_9 | 417-530 plateau; d2+d3 142 |
| 6 | Q_9 | solved, 4 of 4 seeds |
| 6 | Q_10 | lowest 55 seen; 16 seeds, then the best 8 to the 2 CPU-hour cap (1.6e9 moves), all between 55 and 143, still improving slowly; about half of the residual at distance 3, a third at distance 5; d2+d3 only: lowest 133 and 245 |
| 7 | Q_10 | solved, 4 of 4 seeds (42.5M to 73.5M moves) |

Best words found give R(Q_n) <= 4, 4, 4, 5, 5, 6, 7 for n = 4, ..., 10. Each extra dimension beyond
Q_8 costs one more copy in these words. This is an observation about the annealer, not a theorem,
and Q_10 with k = 6 is unresolved: the best run was still improving slowly when the cap stopped it.

## 6. Literature (checked 2026-09-30)

* Hefty, Horn, Muir, Owens, *Word-representable graphs: orientations, posets, and bounds*, Electron.
  J. Combin. 31(4) (2024) #P4.2. Theorem 28: R(Q_n) = O(log n / log log n), via boxicity and the
  dimension of the height-2 poset. Remark 29 asks whether R(Q_4) = 4; section 7 below answers this
  computationally.
* A search-engine summary attributes R(Q_n) = Omega(log log n) to a recent paper (possibly
  *Word-representation numbers of graphs: Bottlenecks and bounds*, JCTB 2026). I could not open it;
  treat as unverified.
* Mozhui-Krishna (arXiv 2506.01057) and arXiv 2609.35842 bound the representation number of arbitrary
  bipartite graphs by about a quarter of the number of vertices. That is useless for Q_n (2^n
  vertices).

## 7. R(Q_4) = 4, re-derived from the definition

`lab/direct_cnf.py` encodes "there is a linear order on the k 2^n occurrences in which x and y
alternate iff xy is an edge" directly, with no height function and no event order (first letter 0
WLOG by cyclic shift). Kissat 4.0.4 returns:

| graph | k | result |
|---|---|---|
| Q_2 | 1 | UNSAT |
| Q_2 | 2 | SAT |
| Q_3 | 2 | UNSAT |
| Q_3 | 3 | SAT (decoded word checked) |
| Q_4 | 3 | UNSAT (1160 variables, 104k clauses) |
| Q_4 | 4 | SAT (decoded word checked) |
| Q_5 | 3 | UNSAT |
| Q_5 | 4 | SAT |

With the witnesses this gives R(Q_4) = R(Q_5) = R(Q_6) = 4. The UNSAT answers are from one solver with
no proof check, so they are a strong computational confirmation, not a certificate.

## 8. Files

`lab/flip.py` (simulator), `identities.py`, `profiles.py`, `rounds.py`, `cones.py`, `wrmodel.py` (exact
distance-2/3 checker for a system of round permutations, validated on real words),
`threshold_search.py`, `direct_cnf.py`, `decode.py`.
