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
> For Q₇ the instance is split exhaustively into three cases (§6). Each case is being
> solved with CaDiCaL in restartable segments, and every segment is checked by the
> formally verified checker cake_lpr (§7). No case has been refuted yet, so the claim is
> **not yet established** by this directory.

<!-- RESULTS-PLACEHOLDER -->

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
