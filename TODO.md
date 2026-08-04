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

- [ ] **Merge two TAs' exports into one weekly file.** Concatenation, since
      the group ranges are disjoint, plus the cross-TA duplicate check neither
      phone can do alone — neither knows what the other recorded.
- [ ] **Backup to OneDrive.** Explicit copy into
      `OneDrive-ReykjavikUniversity`, not an automatic sync, so student data
      never moves without an intentional step.
- [ ] **Decide how the app reaches the phones.** GitHub Pages serves the repo
      root or `/docs`, not `/app` — so either move the file or serve from
      root. Then the TAs get a URL instead of a file.
- [ ] **Confirm the repo's visibility on GitHub.** The code carries no student
      data either way, but if it is public the ignore rules are load-bearing
      rather than merely tidy.
- [ ] **Dry run with both TAs before students are involved.** Two phones, the
      sample roster, fifteen groups each, export, merge. Cheaper to find the
      problems now than in a classroom.
- [ ] **Replace the placeholder factors** with the real ones. Participation,
      preparation, collaboration and progress are guesses.

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

- Does a group score attach to every student in it, or should individual
  deviation be recordable? The current model scores the group only.
- Is `Below / Expected / Above` the right scale once TAs have used it for real?
  Changing it after data exists means two incompatible scales in one semester.
- Should the two TAs' group ranges be fixed all semester, or rotate? Rotating
  gives every student both raters and makes the scores more comparable.
