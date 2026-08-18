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
      synthetic data covering all five cases; not yet run against a real
      export. With no arguments it reads the shared OneDrive Uploads folder
      directly; pass paths explicitly to merge a specific subset instead.
      **Still open:** the agreement figure is plain percent-match, which is
      fine for a first look but not the real statistic (see the script's
      docstring — a weighted kappa or similar belongs in the actual analysis,
      using `groups.csv` as input). And there is no way yet to check a found
      overlap against which weeks were *meant* to be calibration weeks,
      because that schedule doesn't exist yet — tie it to the sealed weekly
      TC/OC allocation once that's built.
- [x] **Populate the second half-day from "who's left."** No section field,
      no pre-known split, no Akureyri exclusion list. The first block of a
      week is a plain roster search; the picker for any later block that week
      defaults to students not yet recorded elsewhere on this phone — with
      search and a "Show everyone" toggle as the override for the rare
      student in both, or a correction.
- [ ] **The "remaining" filter is per-device only.** It only knows what is on
      the phone doing the recording. If a second TA covers the other half on
      a different device, this phone can't see their taps, so the filter
      falls back to showing everyone. Worth deciding whether the merge step
      should cross-check the two devices' populations for a given week and
      flag it if they overlap more than a deliberate calibration week
      intends.
- [ ] **Decide how the TC/OC allocation reaches the app.** Currently the TA
      picks it per block, which is one tap and one chance to get it wrong; a
      wrong value corrupts the primary comparison. Option: pre-load the sealed
      weekly allocation as a small JSON the app reads, leaving the TA to
      confirm rather than choose.
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
- [ ] **Decide how the app reaches the phones.** GitHub Pages serves the repo
      root or `/docs`, not `/app` — so either move the file or serve from
      root. Then the TAs get a URL instead of a file.
- [ ] **Confirm the repo's visibility on GitHub.** The code carries no student
      data either way, but if it is public the ignore rules are load-bearing
      rather than merely tidy.
- [ ] **Dry run with all three TAs before students are involved.** Three phones, the
      sample roster, fifteen groups each, export, merge. Cheaper to find the
      problems now than in a classroom.
- [x] **Replace the placeholder factors** with the real ones — engagement and
      collaboration with behavioural anchors, progress read off the group's
      work, and a stop-thinking question tally. Anchors still want piloting in
      the dry run, then freezing at week 1: changing them mid-semester leaves
      two incompatible scales in one dataset.

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
