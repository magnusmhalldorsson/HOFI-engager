# HOFI-engager

Managing groups and engagement in the HOFI class, DCS/RU fall 2026.

A weekly record of who sat in which group and how engaged that group was, for
*Hugsun og færni í tölvunarfræði* — 90 students, 30 groups, 3 TAs filling 2
recording slots, 12 weeks.

## Where things live, and why

| | |
|---|---|
| **This directory** | `~/Projects/hofi-engagement` — deliberately *not* inside Dropbox or OneDrive |
| **Code** | safe to put in git; contains no student data |
| **`data/`** | roster and recordings; gitignored, never synced automatically |
| **Backup** | TAs upload straight to a folder Magnús shares with them on RU's OneDrive |
| **Canvas token** | macOS Keychain, service `hofi-canvas`; env var or gitignored `config.json` as fallbacks |

The separation is the point. Student names and engagement scores are personal
data held at an EEA institution, so the fewer places they exist the better.
Code can live anywhere; the data lives here and in RU's OneDrive, and nowhere
else. Nothing syncs student data to a personal account by accident.

## Setup

**Every command below runs from the repo root**, `~/Projects/hofi-engagement`.
The script resolves its own paths from there, so `cd` first:

```sh
cd ~/Projects/hofi-engagement
```

Create a Canvas token at **Account → Settings → New Access Token**, leaving the
expiry blank so it does not need renewing. Store it in the Keychain once — you
type it at the prompt, it goes straight in, and it is never on disk in the
clear. This one works from any directory:

```sh
security add-generic-password -a "$USER" -s hofi-canvas -U -w
```

The `-U` matters: without it a second run adds a *duplicate* entry instead of
replacing the old one, and the stale copy may be the one read back — which
shows up later as a 401 that survives making a new token.

Confirm it took. This reports the source and length and asks Canvas who you
are, without ever printing the token:

```sh
python3 scripts/fetch_roster.py check
```

A healthy result says `auth : ok` and names you. If the length is under 40
characters, the stored value is not a Canvas token — those are 60–80
characters, shaped like `1234~AbCdEf…`.

Then, from the repo root:

```sh
cp config.example.json config.json      # fill in canvas_host
```

```sh
python3 scripts/fetch_roster.py courses  # prints your course ids
```

Put the right id into `config.json` as `canvas_course_id`. Either column works
— the numeric Canvas id, or RU's SIS id in the
`DCS-T-101-HOFI:41057:20263` form. They are **not** the same number: the
numeric id is Canvas's own and appears in the course URL, while the SIS id
comes from the student system. Resolving an SIS id needs the right permission
on your Canvas account; if it 404s, fall back to the numeric id.

Then:

```sh
python3 scripts/fetch_roster.py roster   # writes data/roster.json
```

Re-run whenever enrollment changes. It prints what changed:

```
Wrote data/roster.json (98 students).
  + Kári Helgason
  - Telma Arnardóttir
```

### Everyone is on the roster, on purpose

The roster includes **every** enrolled student — including anyone taught
elsewhere (Akureyri). There is no pre-filtering, and that is deliberate: the
app only ever records a student when a TA taps them in, so someone who never
attends a Reykjavík session simply never appears in any block's data. There is
nothing to exclude in advance, and so nothing that can go stale or need
maintaining.

### There is deliberately no section per student, either

*Which* students end up in the room together is redrawn weekly and can change
on the day, and it is *not* a language split — the IS/EN division is not known
to this app at all. Any per-student section stored here would be stale by
week 2 and would quietly mislead, so the roster carries none.

Membership is entirely **observed**: whoever a TA taps in during a session
*is* that session's population. What the app *does* ask for explicitly is
**which cohort group** a Thinking Classroom session is — Group 1 or Group 2,
the two halves that swap Main/Extra room partway through a TC half-day (Group
1 does Thinking Lab then Skill Lab; Group 2 the other order). That label has
real, fixed meaning — it is not the same thing as the arbitrary weekly split —
so it is a required, explicit choice, never inferred. Ordinary class has no
such split; everyone is together as one block.

Standard library only — nothing to install, runs on the system Python.

## What a recording covers

Recording happens **only in the Thinking Lab**, and the unit is a **block** —
one week, one half-day, plus a cohort group when the pedagogy is TC:

    w05-AM        week 5, before lunch, Ordinary class — one block, everyone together
    w05-AM-G1     week 5, before lunch, Thinking Classroom, Group 1
    w05-AM-G2     week 5, before lunch, Thinking Classroom, Group 2

An OC half-day is one block. A TC half-day is **two** — Group 1 and Group 2,
recorded separately because the room-swap genuinely splits the cohort into two
populations with two different orders (TC-first vs Skill-Lab-first), and that
order is worth keeping as data, not collapsing away.

Each block records which pedagogy ran in it — **TC** (Thinking Classroom) or
**OC** (ordinary class) — which is the comparison the study turns on, so it is
a required field rather than an optional label. A block does not pre-declare
*who* it covers beyond that — the population is whichever students actually
get tapped in.

## A TA's process: select session, record, upload

The roster is loaded onto a phone **once**, when the phone is first set up.
It does not get reloaded week to week — opening the app takes a TA straight to
session selection, every time, for the rest of the semester. A student who
drops out is not removed; they simply stop being tapped into any session,
which is exactly how their absence should read.

1. Students pick cards; the card is the group number.
2. **Select the session** — week, half-day, pedagogy. If the pedagogy is
   Thinking Classroom, also pick **which cohort group** this is, Group 1 or
   Group 2 — check it against the day's actual room assignment, not memory.
   Ordinary class has no group to pick; everyone is together.
3. Work through the table-groups: tap the students at the table, rate
   engagement and collaboration, mark how far the group got, and rate how
   often they asked to be told rather than checking their own thinking.
   **No network needed.**
4. **Group 2's picker defaults to showing only students not already recorded
   in Group 1** that same TC half-day — normally exactly who's left, since the
   two groups between them cover the whole Thinking-Lab population. A "Show
   everyone" toggle and the search box both bypass the filter, for the rare
   student in both, or a correction. Ordinary class always shows the full
   roster — there is no pairing to filter against, since everyone attends it
   together.
5. Everyone tapped in counts as present *and* taking part. The `!` flag marks
   the exception — someone who took no part. Recording exceptions rather than
   ticking every student is what keeps this feasible at ~15 groups in 40
   minutes.
6. Anyone never tapped in was not recorded in that session.
7. **Tap a group's dot, at the top of the screen, to jump straight to it** —
   useful for the expected rhythm of composing every group first and rating
   them all near the end. A dot fills in once that group has students, all
   three ratings, and a progress mark; a small counter under the dots tracks
   how many are done, and a checkmark appears next to the group number itself
   once the one you're on is complete.
8. **After the session, upload.** On a phone this hands the file to the OS
   share sheet — the TA picks OneDrive, then the shared HOFI folder. On a
   computer (or any browser that can't share files) it downloads a file
   instead, for AirDrop or mail as a fallback. Either way it uploads
   *everything currently on the phone*, not just what's new — see the merge
   step below for why that's the right behaviour, not a bug.

The Group-1/Group-2 filter only knows what is on **this** phone. If a second
TA covers the paired group on a different device, this phone has no way to
see their data, and the filter falls back to showing everyone.

**Overlapping coverage is expected, not an error.** The two TAs on duty may deliberately
rate the same groups for the inter-rater agreement check, so the merge keeps
both records rather than de-duplicating them. The one real error case is the
same student tapped into two groups *within one session*; the app flags it in
the upload summary.

## Merging the TAs' exports

```sh
python3 scripts/merge_exports.py
```

With no arguments this reads everything the TAs have uploaded to the shared
OneDrive folder — `HOFI26/Uploads`, synced locally at
`~/Library/CloudStorage/OneDrive-ReykjavikUniversity/HOFI26/Uploads/`. Pass
explicit paths instead (`python3 scripts/merge_exports.py data/exports/*.json`)
to merge a specific subset, or files that live somewhere else.

Writes `data/merged/blocks.json` (canonical per-block record, with an
`issues` list) plus `groups.csv` and `membership.csv` for stats software.
Merged output stays local — only the raw per-TA exports live in OneDrive.

Takes the newest export per TA — each export is a full snapshot, so a later
one supersedes an earlier one for that TA. From there it unions split
coverage, keeps both records on a deliberate overlap (a calibration week —
two TAs rating the same groups) and reports a first-pass agreement figure,
flags it if TAs disagree on which pedagogy a block was, and catches the one
error neither phone can see alone: the same student recorded under two
different group numbers by two different TAs. `not_seen` is recomputed from
the union of everyone actually recorded, not trusted from any single file.

The agreement figure is plain percent-match — good enough to sanity-check a
dry run, not the statistic for the actual analysis (see the script's
docstring for why).

## Two records, one session

The app keeps the grading record and the research record apart, because they
are different instruments and mixing them damages both:

| | Grading | Research |
|---|---|---|
| Unit | Individual student | Group |
| What | A 3-point scale per student: not tapped in (absent), tapped in (participated), tapped in and flagged with `!` (present but did not participate) | Engagement, collaboration, stop-thinking, progress — per group |
| Opt-out | No — it is how the course is assessed | Yes |

The reasoning is in the vault: `10-AI-and-Education/04-Projects/HOFI/Research/`
— see *HOFI Measurement Plan* for the instruments and *HOFI Study Design* for
what the blocks feed into.

## Status

Recording works end to end: pull the roster, import it on each phone, record
blocks offline, export. Still missing: merging the TAs' files, backup, and
analysis. See [TODO.md](TODO.md), the single list.

## Configuration

Measures are configuration, not code — `RATINGS` and `PROGRESS` at the top of
the app. Adding one mid-semester is a few lines, and earlier blocks simply
carry no value for it.

- **Engagement**, **Collaboration**, and **Stop-thinking questions** —
  Below / Expected / Above, each level carrying a behavioural anchor the TA
  can expand by tapping the measure name. Stop-thinking was originally a
  tally ("is this right?"), but keeping an accurate count proved impractical
  mid-session, so it moved to the same 3-point scale as the other two. The
  anchors are deliberately written so they can be observed in *either*
  condition; nothing refers to the whiteboard, because an ordinary class has
  none and a measure that means different things in the two arms cannot
  compare them.
- **Progress** — None / Partial / Complete / Extended, read off the group's
  work rather than judged.

Three levels rather than four is deliberate: fewer options means faster
decisions and better agreement between raters.
