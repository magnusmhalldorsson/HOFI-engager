# R(Q₇) > 4: the 7-cube is not 4-representable

**Goal.** Show that the 7-dimensional hypercube Q₇ has no 4-uniform word-representant,
so that its representation number satisfies R(Q₇) ≥ 5.

The approach has two parts:

1. A structure theorem, proved by hand below. It turns a k-uniform representant of Qₙ
   into a periodic *event order* governed by a height function on Qₙ.
2. A finite, fully specified CNF (`event_cnf.py`). Every clause of the CNF is satisfied
   by the event order of any 4-representant of Q₇, after a harmless normalisation. So
   an unsatisfiability certificate for the CNF proves the claim.

> **Status: work in progress.** Part 1 is complete. For n ≤ 6 the machinery reproduces
> R(Q₃) = 3 and R(Q₄) = R(Q₅) = 4, and shows that Q₆ is 4-representable. These results
> are cross-checked against a theory-free encoding, and explicit witness words are in
> `witnesses/`.
>
> For Q₇ the current targets are the window CNF WR(7, 4) of §6a and its relaxations CRR
> and PFR+ (§6a, §6b). WR is an exact encoding of the distance-2/3 part of the problem,
> with 51k variables and 4.4M clauses, and it needs no case split. PFR+ is the smallest
> sound formula so far (23k variables, 0.22M clauses). Solvers are running on them, one as
> a restartable CaDiCaL chain checked by cake_lpr (§7). The earlier three-case instances
> of §6 are paused.
>
> No instance has been refuted yet, so the claim is **not yet established** by this
> directory. There is also a real risk that the distance-2/3 part alone is satisfiable
> for (7, 4). It is satisfiable for (4, 3) even though R(Q₄) = 4, see §6b. In that case
> only the all-distance encodings (§5, §6, `ball_event_cnf.py`) can succeed.

<!-- RESULTS-PLACEHOLDER -->

> **Heuristic evidence (not a proof).** `search/sa.c` is a weighted local search over
> cyclic words in which every edge pair alternates. It finds 4-representants of Q₄, Q₅
> and Q₆ within seconds to a few minutes. Every Q₆ result is verified by
> `check_word.py`, including the case where only distance-2 and distance-3 pairs are
> constrained.
>
> On Q₇ it stalls far from a solution: the best word leaves 86 of 7680 non-adjacent pairs
> alternating after 10⁹ moves. It still stalls at 23 when only pairs at distance 2 and 3
> are required not to alternate (3.4·10⁹ moves). With distance 2 alone it finds a word at
> once, and with distance 3 alone it gets within 2 violations. On Q₄, Q₅ and Q₆ with
> k = 3, all of which are known to be non-representable, it behaves the same way.
>
> This suggests that the obstruction already lives in the distance-2 and distance-3
> pairs. `window_cnf.py` (§6a) encodes exactly that part of the problem. `local_cnf.py`
> and `crr_cnf.py` encode weaker relaxations. The unsatisfiability of any of them would
> suffice. For k = 3 all three already refute Q₅.

---

## 1. Definitions and two standard facts

A word *w* over V(G) **represents** G if, for all distinct x, y, the letters x and y
alternate in *w* (the subword on {x, y} is xyxy… or yxyx…) exactly when xy ∈ E(G). The
word is **k-uniform** if every letter occurs exactly k times. R(G) is the least k for
which a k-uniform representant exists.

* **(F1)** A cyclic shift of a uniform representant is again a representant
  (Kitaev–Pyatkin). So a uniform representant is really a *cyclic* word.
* **(F2)** If G is k-representable, so is every induced subgraph. In particular
  R(Q₇) ≥ R(Q₆) ≥ … .

Vertices of Qₙ are the vectors of {0,1}ⁿ, written as integers. d(x, y) is Hamming
distance and |x| is the weight. The graph is bipartite, and its 4-cycles
x, x+eᵢ, x+eᵢ+eⱼ, x+eⱼ are all induced.

From now on, *w* is a k-uniform cyclic word representing Qₙ, with n ≥ 2.

## 2. The square lemma

**Lemma 1.** Let a–b–c–d–a be a 4-cycle of Qₙ. Read cyclically, the restriction of *w*
to {a, b, c, d} has the form P₁Q₁P₂Q₂⋯P_kQ_k with Pᵢ ∈ {ac, ca} and Qᵢ ∈ {bd, db}.

*Proof.* The letter a alternates with both b and d. So between two consecutive a's there
is exactly one b and exactly one d, and w|{a,b,d} = a B₁ a B₂ ⋯ a B_k with
Bᵢ ∈ {bd, db}. The Bᵢ are not all equal, because b and d do not alternate. The same
statement holds for c. The cyclic word w|{b,d} has length 2k and exactly two
decompositions into consecutive 2-letter blocks. Take the one given by a. Where
Bᵢ ≠ Bᵢ₊₁, the other decomposition has a block made of the last letter of Bᵢ and the
first letter of Bᵢ₊₁, which is bb or dd. Hence c sits in the same k gaps of w|{b,d} as
a. ∎

## 3. Height function and event order

Cut the cyclic word anywhere. For an edge xy let σ(x→y) = +1 if the first x after the
cut comes before the first y, and σ(x→y) = −1 otherwise.

**Lemma 2.**
(a) Around every 4-cycle, the sum of σ is 0.
(b) There is h₀ : V → ℤ with h₀(y) − h₀(x) = σ(x→y) on every edge. We normalise
    h₀(0) to be even, so that h₀(x) ≡ |x| (mod 2).
(c) Read *w* from the cut, and at each occurrence of x replace h(x) by h(x) + 2. Then
    at every occurrence of x, every neighbour y of x has h(y) = h(x) + 1.

*Proof.* (a) Walk around the cycle a→b→c→d→a. By Lemma 1, the cut falls either between
two blocks, or inside a P-block, or inside a Q-block.

* Just before a P-block, a and c come first, so the signs are (+, −, +, −).
* Between the two letters of a P-block, the order of first occurrences is c, then b and
  d, then a, so the signs are (−, −, +, +).
* The two Q cases are the same with the roles of {a, c} and {b, d} exchanged.

In every case the four signs sum to 0.

(b) Part (a) says that σ is a 1-cocycle on the 2-skeleton (vertices, edges, squares) of
the n-cube. That complex has H¹ = 0, because the cube is contractible, so σ is a
coboundary.

(c) Invariant: for every edge xy, h(y) = h(x) + 1 exactly when the next x comes before
the next y. It holds at the cut by definition. It is preserved at an occurrence of x
because x alternates with each of its neighbours, and it is unaffected for other
edges. ∎

The **event (x, r)** is the occurrence of x at which h(x) = r. Extending *w*
periodically to a bi-infinite word, events exist exactly for r ≡ |x| (mod 2). Their
order ≺ in the bi-infinite word is a linear order, periodic with period 2k in r.
Moving the cut only adds a constant to all labels.

**Lemma 3.** For all x, y and r, s:

* **(E1)** If xy is an edge: (y, r−1) ≺ (x, r) ≺ (y, r+1).
* **(E2)** (Light cone) (x, r) ≺ (y, s) whenever s − r ≥ d(x, y).
* **(E3)** (x, r) ≺ (y, s) if and only if (x, r+2k) ≺ (y, s+2k).
* **(E4)** Suppose xy is not an edge, and let d = d(x, y) ≥ 2. Define
  g(r) = #{ s : |s − r| < d, (y, s) ≺ (x, r) }.
  Then g is not constant over the k ranks r of x in one period.

*Proof.* (E1) is Lemma 2(c). (E2) follows by chaining (E1) along a geodesic.

For (E4): by (E2), every y-event of rank ≤ r − d precedes (x, r), and every y-event of
rank ≥ r + d follows it. So the number of y's strictly between (x, r) and (x, r+2) is
1 + g(r+2) − g(r). Now x and y alternate exactly when that number is 1 for every r,
that is, exactly when g is constant. ∎

## 4. Normalisation

An **arc** is the stretch strictly between two consecutive occurrences of a letter.
Choose an arc of minimum length. Then no letter occurs twice inside it, since otherwise
that letter would span a shorter arc. Now apply three harmless changes:

* translate by the arc's letter (an automorphism of Qₙ);
* recompute the labels and shift them, keeping h₀(0) even, so that the arc runs from
  (0, 0) to (0, 2);
* permute coordinates so that the neighbours e₁, …, eₙ of 0 occur inside the arc in
  this order.

Arc lengths are preserved throughout.

## 5. The CNF (`event_cnf.py`)

**Variables.** One variable for each *undetermined* event pair, meaning a pair
((a, r), (b, s)) with a < b and |s − r| < d(a, b), taken modulo (E3). The variable is
true when (a, r) ≺ (b, s). All other pairs are fixed by (E2).

**Clauses.** The event order of a normalised representant satisfies every clause below.

| family | clause | why it holds |
|---|---|---|
| closure | for each event e and edge-step f = (a,r) → f′ = (b,r+1) with f, f′ undetermined relative to e: [f′ ≺ e] → [f ≺ e] | f ≺ f′ by (E1), and ≺ is transitive |
| nonalt | for each non-edge ab: some offset δ ∈ {−(d−2), …, d−2} (step 2) with r ↦ [(b, r+δ) ≺ (a, r)] non-constant | g is the sum of these indicators, so (E4) |
| sym | (eᵢ, 1) ≺ (eᵢ₊₁, 1); and no vertex has two consecutive events inside (0,0) → (0,2) | §4 |
| samerank (optional) | no directed 3-cycle among three events of equal rank | ≺ is linear |
| all (optional) | no directed 3-cycle among pairwise undetermined events | ≺ is linear |

The first three families together are the *base* instance; `--tri samerank` adds the
fourth. Dropping clauses only weakens an instance. So unsatisfiability of the base or
samerank instance already proves the claim.

**Consequence.** If the CNF for (n, k) = (7, 4) is unsatisfiable, Q₇ is not
4-representable.

## 6. Case split on the antipodal lag (`antipodal_cases.py`)

For an event (x, r), let x′ = x ⊕ 11…1 be the antipode of x, and define the **antipodal
lag** A_x(r) = H_{x,r}(x′) = 2g(r) − (n − 2). Here g(r) counts the undetermined
x′-events that precede (x, r).

**Lemma 4.** For n = 7, the maximum lag M = max A_x(r) lies in {3, 5, 7}.

*Proof.* Fix an antipodal pair. Each of its 4(n−1) undetermined event pairs per period
is counted exactly once, either in some g_{x,x′} or in some g_{x′,x}. So the lags of
the pair average to 1. If every lag were ≤ 1, every lag would equal 1, g would be
constant, and x, x′ would alternate. Lags are odd when n is odd. ∎

Two further facts are used:

* The same monotonicity gives A_x(r+2) ≥ A_x(r) − 2.
* A maximiser followed by a maximiser in every round would make the lag constant. So
  some maximiser (x, r) has A_x(r+2) = M − 2.

The three cases, with the normalisation each allows:

| case | assumption | normalisation |
|---|---|---|
| I | every lag ≤ 3 | shortest arc at (0, 0), as in §4 |
| II | every lag ≤ 5; A₀(0) = 5 and A₀(2) = 3 | maximiser followed by a drop, moved to (0, 0) |
| III | A₀(0) = 7 and A₀(2) = 5 | maximiser followed by a drop, moved to (0, 0) |

In all three cases the coordinates are then sorted inside the arc (0,0) → (0,2). The
bound in case I is global and invariant under symmetries, which is why the shortest-arc
normalisation is still available there. `case_split_test.py` checks every clause of the
right case against normalised genuine representants.

In case III, vertex 0's whole view is the cone H(v) = |v|. A genuine Q₆ representant
with such a cone exists (`witnesses/q6_k4_cone.txt`), so this case cannot be dismissed by
restricting to a 6-dimensional layer.

## 6a. Distances 2 and 3 only: the window CNF (`window_cnf.py`)

For a non-edge xy with d(x, y) = d, condition (E4) mentions only the event pairs
((x, r), (y, s)) with |s − r| < d. For d = 2 these have s = r, and for d = 3 they have
|s − r| = 1. So the non-alternation of all pairs at distance 2 or 3 is a statement about
events of equal or adjacent ranks.

For r ∈ ℤ, let the **window** W_r be the set of events of rank r or r + 1.

**Lemma 5.** Let ≺ be the event order of a k-uniform representant of Qₙ, and let ≺_r be
its restriction to W_r. Then:
(W1) each ≺_r is a linear order with (y, r) ≺_r (z, r+1) for every edge yz;
(W2) ≺_r and ≺_{r+1} agree on the events of rank r + 1;
(W3) the family is periodic: shifting all ranks by 2k maps ≺_r to ≺_{r+2k};
(W4) (E4) holds for every pair at distance 2 or 3.

This is immediate from Lemma 3. `window_cnf.py` writes (W1)–(W4) as a CNF WR(n, k): one
variable per undetermined pair inside a window, all transitivity triangles inside each
window, the non-alternation clauses for d ∈ {2, 3}, and the clauses of §4 that live
inside windows. Every clause is a clause of `event_cnf.py --tri all` restricted to window
pairs, so:

**Consequence.** If WR(7, 4) is unsatisfiable, then Q₇ is not 4-representable.

**Remark (why this is the right relaxation).** The converse of Lemma 5 also holds. Any
family (≺_r) with (W1)–(W3) glues to a periodic event order. Two linear orders that agree
on the intersection of their ground sets amalgamate without cycles, so the union of the
windows of any finite rank interval is acyclic, and hence so is the union of all windows.
A shift-invariant acyclic relation in which every event precedes its own shift has a
shift-invariant linear extension (a periodic time function exists because every cycle of
the quotient graph has positive total shift).

So WR(n, k) is satisfiable exactly when there is a k-uniform word in which every edge pair
alternates and no pair at distance 2 or 3 alternates. `window_cnf.py` is thus an *exact*
encoding of that problem, not merely a relaxation. The gluing has been checked on
solver models for (n, k) = (4, 3), (5, 4) and (6, 4); the glued words were verified
letter by letter.

**Normalisations.** Two alternative normalisations are available (`--norm`):
* `shortest` (§4): the arc (0,0) → (0,2) is a globally shortest arc;
* `lag`: (0,0) maximises the lag t(e) − (L/2k)·rank(e) over all events e, where t(e) is
  the position of e in the bi-infinite word and L = k·2ⁿ. Lags are periodic, so a
  maximiser exists. Every event f of rank ≤ 0 then satisfies t(f) ≤ t(0,0), hence
  precedes (0,0). At that moment vertex 0 is the unique global minimum of the height
  function.
Both are followed by sorting the neighbours of 0 inside the arc (0,0) → (0,2).

With `shortest`, the map ρ : (a, r) ≺ (b, s) ↦ (π b, 2 − s) ≺ (π a, 2 − r) is a symmetry
of the CNF. Here ρ is time reversal combined with reversing the coordinate order π. It
maps windows to windows, the arc (0,0) → (0,2) to itself, and the neighbour order to
itself. This was checked clause by clause for n = 4, 5, and ρ maps models to models.
`--revlex m` adds the lex-leader constraint X ≤_lex ρ(X) on m variables of the view of
(0,0). Either a normalised order or its reverse satisfies it.

**Wider windows.** With `--width W` the windows contain W consecutive ranks, and
non-alternation can be imposed for all distances d ≤ W + 1 (`--dset`). The same gluing
argument applies. For example, `--width 3 --dset 2,3,4` is exact for Q₄ and refutes k = 3
there, which reproduces R(Q₄) > 3.

**A smaller relaxation (`crr_cnf.py`).** Keep only the orders inside single ranks. An
inversion (d, w+1) ≺ (c, w) at distance 3 forces two things: every neighbour of d
precedes c in rank w, and d precedes every neighbour of c in rank w + 1. So (E4) at
distance 3 requires some window in which both hold. Together with (E4) at distance 2,
this gives CRR(n, k), with about 0.9M clauses for (7, 4). Its normalisation makes (0,0)
the last event of rank 0, by translation, and sorts the neighbours of 0 in rank 1. It
refutes k = 3 for Q₅ and is satisfiable for (6, 4).

**The weakest relaxation (`pfr_cnf.py`).** Keep only the orders of same-rank events at
distance 2. Take a vertex y, one of its arcs (y, s) → (y, s+2), and the order π in which
its neighbours bᵢ = y + eᵢ fire inside the arc (rank s + 1). Let t_{jl} = y + e_j + e_l.
The diagonal (bᵢ, t_{jl}) of the cube y + span(eᵢ, e_j, e_l) needs a cone moment, and y is
frozen during it, so the cone lies inside an arc of y. If the bottom is bᵢ, then b_j and
b_l fire before bᵢ, and t_{jl} precedes y at rank s + 2. If the bottom is t_{jl}, then bᵢ
fires before b_j and b_l, and y precedes t_{jl} at rank s. So bᵢ is last or first among
{bᵢ, b_j, b_l} in π. These conditions, the cone conditions for (y, y + e_T), (E4) at
distance 2 and transitivity on triangles of the halved cube give PFR(n, k). It has 0.56M
clauses for (7, 4), mostly auxiliary definitions. It refutes k = 3 for Q₅ and Q₆, and it
is satisfiable for (6, 4).

`window_soundness_test.py` checks every clause of these CNFs (WR, CRR, PFR, PFR+), under every
normalisation, against normalised genuine representants.

## 6b. Further relaxations, and where the obstruction is not

**PFR+ (`pfrp_cnf.py`).** This uses the same variables as PFR: the orders of same-rank
pairs at distance 2. PFR's cone conditions (C) and (D) are replaced by the exact Q₃
condition they come from:

* (QX) For every Q₃ C and every diagonal {x, x′} of C, some window w has an inversion
  on that diagonal.
* Such an inversion (d, w+1) ≺ (c, w) makes c the last of C's four vertices of parity w
  in rank w, and d the first of C's four vertices of parity w + 1 in rank w + 1. The
  C-neighbours of d precede d, and the C-neighbours of c follow c.

QX implies (C) and (D). Together with star transitivity, (E4) at distance 2 and the
normalisation of CRR, this gives 23k variables and 0.22M clauses for (7, 4). PFR+ is
unsatisfiable for (3, 2), (5, 3) and (6, 3), and satisfiable for (3, 3), (4, 3), (5, 4)
and (6, 4). The soundness test passes on all witnesses.

**The distance-2/3 part is not always enough.** WR(4, 3) is satisfiable, yet R(Q₄) = 4.
`window_cnf.py 4 3 --width 3 --dset 2,3,4` is unsatisfiable, so the antipodal pairs of
Q₄ are what exclude k = 3 there.

In the same way, a symmetric model of WR(6, 4) glues to a word in which every pair at
distance 2 or 3 behaves, but 64 pairs at distance 4 and 16 at distances 5–6 alternate.
So a satisfiable WR(7, 4) would not contradict R(Q₇) > 4.

Against that, the local search of `search/sa.c` behaves as follows:

| instance | pairs required not to alternate | outcome |
|---|---|---|
| (4, 3) | distances 2, 3 | solution after 19k moves |
| (4, 3) | all distances | stalls at 1 violation |
| (6, 4) | distances 2, 3 | solution within minutes |
| (7, 4) | distances 2, 3 | stalls at 23 violations after 3.4·10⁹ moves |

**No local obstruction for k = 4.**

* *The k = 3 refutations are local.* A minimal unsatisfiable subformula of PFR+(5, 3) has
  518 of its 12,014 clauses. It uses 42 diagonal conditions, 32 of them from the ten Q₃'s
  through the normalised vertex 0.
* *PFR+(7, 4) on balls.* Restricted to Hamming balls, it is satisfiable within a second
  for:
  * radius 2, 3 and 4 around 0 (29, 64 and 99 vertices);
  * radius 2 and 3 around an edge;
  * radius 2 around a square or a Q₃.
* *WR(7, 4) on balls.* The exact window CNF (lag normalisation) restricted to the balls
  of radius 3 and 4 around 0 is satisfiable.
* *All distances on a ball.* `ball_event_cnf.py` gives the all-distance event CNF of
  §5 with full transitivity, restricted to a ball around 0, with the lag normalisation.
  Distances inside a ball around 0 are distances in Q₇, so this is sound; it passes a
  soundness test on the witnesses. It refutes k = 3 on B₃(0) ⊂ Q₅ and on Q₄ itself. For
  (7, 4) it is satisfiable on B₃(0), and the run on B₄(0) (60k variables, 4.9M clauses)
  is in progress.
* *Backbone of PFR+(6, 4).* The literals common to all solutions of the normalised
  PFR+(6, 4) are only the normalisation and its transitive closure. The tight case n = 6
  therefore has no rigid structure to transfer to the seven Q₆ faces of Q₇ through 0.

**Simple counting cannot decide k = 4.** At every rank, each Q₃ has exactly one last and
one first vertex among its four vertices of that rank's parity. An inversion in window
w on a diagonal of C needs last_w(C) and first_{w+1}(C) to be antipodal. So every Q₃
needs at least 4 of its 2k (Q₃, window) slots.

For k = 4 that is half of all slots, independent of n. A single window can serve all
Q₃'s at once, which a local search over round orders achieves easily. The best Q₇ word
found uses 68% of all slots (the Q₆ witness uses 60%). Yet 33 of its Q₃'s see only three
of their four diagonals. The difficulty is therefore diversity (every Q₃ must be a cone
at all four apex classes over the period), not the number of inversions.

A bound via "escapes" fails similarly. An inversion needs the later endpoint to lie outside
the span of the other endpoint's neighbours in the round orders of both ranks, and some
round order already gives such escapes for half of all distance-3 pairs.

**Permutational representants (`poset_dim_cnf.py`).** A word L₁L₂L₃L₄ made of four
permutations of V(Qₙ) represents Qₙ iff the Lᵢ realise the height-2 poset Pₙ (even < odd
neighbour). Kissat shows dim(P₃) ≤ 4 and dim(P₄) ≤ 4, but dim(P₅) > 4. So no Qₙ with
n ≥ 5 has a permutational 4-representant.

**Symmetric ansätze (`symmetric_ansatz.py`).** A symmetry of a representant maps (v, r)
to (g v, ±r + c) for an automorphism g of Qₙ. A symmetry fixing every rank is trivial,
so the symmetry group embeds in the dihedral group of order 4k acting on ranks. The script
imposes invariance under chosen generators on WR(n, k), rejecting groups that do not act
faithfully on ranks. A satisfying assignment glues to a word as in §6a; an unsatisfiable
ansatz proves nothing.

For (6, 4):
* Invariance under v ↦ v ⊕ 0000011 with a rank shift of 4 is satisfiable.
* Invariance under the order-8 map g = t_{e₀} ∘ (0 1 2 3) (rotate coordinates 0–3, then
  flip coordinate 0) with rank shift 1 is satisfiable.
* Several other cyclic groups are satisfiable, as is the reflection
  (v, r) ↦ (v ⊕ 000011, −r).
* All 48 dihedral groups of order 16 that were tested are unsatisfiable.

For (7, 4):
* The same order-8 map g = t_{e₀} ∘ (0 1 2 3) with rank shift 1 gives an unsatisfiable
  ansatz within minutes.
* Order-4 and order-2 ansätze ran out of the 25-minute budget.

## 7. Certificates (`certify/`)

Container restarts make single long solver runs impractical here. Each case is instead
solved in segments by `certify/segdriver.py`:

* Segment i runs CaDiCaL for at most 20 minutes on Fᵢ, writing a binary LRAT proof.
* When a segment ends without an answer, `certify/lratx.c` does three things:
  * it takes the longest complete prefix of the proof (this also covers a solver killed
    mid-write);
  * it checks that the prefix contains only RUP steps (positive hints), so every derived
    clause is implied by F₁;
  * it collects the clauses Kᵢ still alive at the end of that prefix, keeping those with
    ≤ 40 literals.
* cake_lpr, a proof checker verified in CakeML, then confirms that the prefix transforms
  Fᵢ into a formula containing Kᵢ ("s VERIFIED TRANSFORMATION").
* The next segment runs on Fᵢ₊₁ = F₁ ∪ Kᵢ.
* A segment that reports UNSAT is checked with cake_lpr against its own input
  ("s VERIFIED UNSAT").

By induction every Fᵢ has exactly the same models as F₁. So one verified refutation of
any Fᵢ refutes F₁. Each case's `ledger.txt` records every segment: its proof hash, the
number of lemmas carried forward, and the checker's verdict.

## 8. Checks of the encoding

* `small_cases.py` solves the event model for n ≤ 5 (and n = 6 with `--q6`). It compares
  every answer with a theory-free encoding: a linear order on all k·2ⁿ occurrences with
  full transitivity. The two models agree everywhere: R(Q₂) = 2, R(Q₃) = 3,
  R(Q₄) = R(Q₅) = 4, and Q₆ is 4-representable.
* `soundness_test.py` takes a genuine representant, verified from the definition by
  `check_word.py`, and normalises it as in §4. It then rebuilds the height function,
  asserting that the potential of Lemma 2 exists, and checks that every clause of all
  three CNF variants is satisfied. It passes on the witnesses in `witnesses/` (Q₃ with
  k = 3; Q₄ with k = 4, 5; Q₅ and Q₆ with k = 4, including the Q₆ witness through a
  cone) and on 38 further random representants with n = 3..5 and k = 3..6.
* The CNF generator was written three times: `event_cnf.py` and two independent
  implementations used during development. All three produce identical clause sets for
  n = 3..7.

## 9. Reproducing

```sh
pip install python-sat                 # for small_cases.py only
python3 check_word.py 6 witnesses/q6_k4.txt
python3 soundness_test.py 6 witnesses/q6_k4.txt
python3 small_cases.py
python3 event_cnf.py 7 4 --tri samerank -o q7.cnf   # sha256 9406d0da...b86f86d
cadical --lrat=true --binary=true q7.cnf q7.lrat
lrat-trim q7.cnf q7.lrat                           # prints "s VERIFIED"
```

The solvers and checkers used were CaDiCaL 2.x, Kissat 4.0.4, lrat-trim 0.2.0, and
lrat-check / drat-trim from the drat-trim repository.
