# TODO

Ordered by what blocks a real week 1. Everything above the line has to work
before the first session; everything below can arrive during the semester.

## Done

- [x] Canvas roster pull — `scripts/fetch_roster.py`, stdlib only, prints a
      diff of who joined and left on re-fetch
- [x] Session recorder — assign students to a group, score the factors,
      works with no network
- [x] Roster import per device — app stays free of student data so it can be
      hosted publicly
- [x] Per-week storage, multiple weeks on one phone
- [x] Export a week as JSON from the phone
- [x] Guards before export — same student in two groups, groups started but
      not finished
- [x] Erase-everything button for end of semester

## Before week 1

- [x] **Merge the TAs' exports.** `scripts/merge_exports.py` — takes the
      newest export per TA, unions split coverage, keeps both records on a
      deliberate overlap and reports provisional agreement, flags condition
      disagreements between TAs, and catches the one thing neither phone can
      see alone: the same student recorded under two different group numbers
      by two different TAs in the same block. Recomputes `not_seen` from the
      union rather than trusting any single export's copy. Tested against
      synthetic data covering all five cases, and run against a real
      export on 2026-08-20. With no arguments it reads the shared OneDrive Uploads folder
      directly; pass paths explicitly to merge a specific subset instead.
      **Still open:** the agreement figure is plain percent-match, which is
      fine for a first look but not the real statistic (see the script's
      docstring — a weighted kappa or similar belongs in the actual analysis,
      using `groups.csv` as input). And there is no way yet to check a found
      overlap against which weeks were *meant* to be calibration weeks,
      because that schedule doesn't exist yet — tie it to the sealed weekly
      TC/OC allocation once that's built.
- [x] **Populate Group 2 from "who's left."** Revised 2026-08-18 once it
      became clear TC and OC halves are not symmetric: a TC half-day
      genuinely splits into two populations (Group 1 / Group 2, the room-swap
      order), so Group 2's picker defaults to students not yet recorded in
      Group 1 that same half-day. The Open Challenge has no split — everyone is
      together — so it always shows the full roster, no filter. Search and a
      "Show everyone" toggle bypass the filter either way.
- [x] **Groups are identified by their card, not by a number.** Changed
      2026-08-20 after MMH confirmed how grouping actually works: students draw
      from a reduced deck (no 10/J/Q/K), so a group is a rank *and* a colour —
      red 7 and black 7 are different groups. At most 15 groups in a room out
      of 18 available cards. The old 1–15 range turned out to be each TA's own
      running counter, mapped to the room by a method nobody recorded, which
      made the group identifier meaningless across TAs and across sessions. The
      card is externally visible to both TAs and the students, so two observers
      of the same group now record the same value — inter-rater agreement can
      be read directly instead of reconstructed from student membership. Export
      schema 4; blocks recorded under the old numbering still open, render and
      export, keeping their numbers. Not yet exercised on a real phone.
      **Still open:** a card names a group only within its room, so the cohort
      holds two red aces. Today that never reaches the data because TAs record
      only in the Thinking Lab, which is room-split — but any recording in a
      whole-cohort block would need the room alongside the card.
- [ ] **The Group 1/2 filter is per-device only.** It only knows what is on
      the phone doing the recording. If a second TA covers the paired group
      on a different device, this phone can't see their taps, so the filter
      falls back to showing everyone. Worth deciding whether the merge step
      should cross-check the two devices' populations for a given block and
      flag it if they overlap more than a deliberate calibration week
      intends.
- [x] **Decide how the weekly allocation — and the cohort group — reach the
      app.** Done 2026-08-21. `scripts/make_allocation.py` draws the whole
      weeks 2–12 order allocation from a recorded seed and writes
      `app/allocation.json`, which the app fetches and caches so it still
      knows the schedule with no network. The chooser now states, for the
      selected week and half, which cohort group takes the Thinking Lab first
      and which follows, and says which week it is talking about — so a wrong
      week number shows up as a mismatch rather than as a plausible line.
      **Shown, never auto-selected:** a wrong cohort group silently creates
      the wrong block, so the app must not guess on the TA's behalf. With no
      allocation fetched the picker behaves exactly as before.
      `--check --seed <seed>` regenerates and compares, which is what makes
      the pre-registration's "seed recorded in advance" a checkable claim.
      **Note on the old wording:** this item used to say *TC/OC allocation*.
      There is no TC/OC allocation — that predates the 2026-08-19 correction
      establishing that no ordinary-class arm exists in the timetable. Both
      half-days have the same structure and nothing is allocated between them.
      **Resolved 2026-08-22:** `OC` means **Open Challenge**, always — the seated
      block that follows the Thinking Lab. There is no ordinary class in this course.
      The app's condition button was mislabelled "Ordinary class"; relabelled, key
      unchanged, so no recorded data needed migrating.
- [x] **Backup to OneDrive.** Decided 2026-08-17: TAs have RU OneDrive
      accounts, so Magnús shares a folder with them directly and the app's
      Upload button shares straight to it via the OS share sheet (falls back
      to a plain download where file-sharing isn't supported). Still an
      explicit, deliberate action each time — not a background sync — so the
      "never moves without an intentional step" principle holds.
- [x] **Point `merge_exports.py` at the real shared folder.** Done 2026-08-17
      — `HOFI26/Uploads`, confirmed synced locally at
      `~/Library/CloudStorage/OneDrive-ReykjavikUniversity/HOFI26/Uploads/`.
      That's now the script's default when run with no arguments.
- [ ] **Try the Upload button on a real phone before the dry run.** The
      share-sheet code (`navigator.share` with a `File`) is correct against
      spec and was verified to fall back to download correctly, but file
      sharing can't be exercised from a desktop or headless browser — the
      only real proof is an actual iPhone/Android tapping Upload and seeing
      OneDrive as a share target.
- [x] **Decide how the app reaches the phones.** Done 2026-08-18 — repo made
      public, GitHub Pages publishes `app/` via Actions on every push. Live at
      `https://magnusmhalldorsson.github.io/HOFI-engager/`.
- [x] **Confirm the repo's visibility on GitHub.** Public, as of 2026-08-18 —
      needed for free GitHub Pages. Confirmed safe before flipping it: the
      code carries no student data, `data/` is gitignored, and the ignore
      rules were audited immediately beforehand.
- [ ] **Dry run with all three TAs before students are involved.** Three phones, the
      sample roster, fifteen groups each, export, merge. Cheaper to find the
      problems now than in a classroom. Should also exercise a TC half-day
      with both Group 1 and Group 2 recorded, not just OC.
- [x] **Replace the placeholder factors** with the real ones — engagement,
      collaboration and stop-thinking with behavioural anchors (stop-thinking
      moved from a planned tally to a rating, since keeping an accurate count
      mid-session proved impractical), plus progress read off the group's
      work. Anchors still want piloting in the dry run, then freezing at week
      1: changing them mid-semester leaves two incompatible scales in one
      dataset.
- [x] **Cohort group (Group 1 / Group 2) for TC sessions.** Added 2026-08-18.
      Selected explicitly by the TA, shown only when pedagogy is TC — Ordinary
      class has no such split. Distinct from the card table-groups;
      see [[HOFI Study Design]] for what the split now means.
- [x] **Completion indicators while composing-then-rating.** Added 2026-08-18
      for the expected TA workflow (seat every group first, rate near the
      end): the dots are now tappable to jump straight to any group, a
      counter under them tracks how many are fully entered, and a checkmark
      appears next to the group number once the current one is done.

## During the semester

- [ ] Analysis over the twelve weeks — per-student engagement given that
      groups change weekly, so a student's record is the sequence of groups
      they sat in
- [ ] Late-joiner handling: re-run the roster fetch, confirm the app copes
      with a student appearing mid-semester
- [ ] A student appearing in neither TA's groups — currently reads as absent,
      which is right, but worth checking it is not masking a mis-tap
- [ ] Retention: decide when the data is deleted, and from where. Phones,
      laptop, OneDrive. Semester end is the obvious answer; it should be a
      decision rather than a drift.

## Open questions

- ~~Does a group score attach to every student in it?~~ Settled: two separate
  records. Group scores for research, an individual present/took-part/flagged
  tick for grading. They are different instruments, not two views of one score.
- Is `Below / Expected / Above` the right scale once TAs have used it for real?
  Changing it after data exists means two incompatible scales in one semester.
- Should the TAs' group ranges be fixed all semester, or rotate? Rotating
  gives every student both raters and makes the scores more comparable.
