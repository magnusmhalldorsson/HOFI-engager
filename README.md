# HOFI-engager

Managing groups and engagement in the HOFI class, DCS/RU fall 2026.

A weekly record of who sat in which group and how engaged that group was, for
*Hugsun og færni í tölvunarfræði* — 90 students, 30 groups, 2 TAs, 12 weeks.

## Where things live, and why

| | |
|---|---|
| **This directory** | `~/Projects/hofi-engagement` — deliberately *not* inside Dropbox or OneDrive |
| **Code** | safe to put in git; contains no student data |
| **`data/`** | roster and recordings; gitignored, never synced automatically |
| **Backup** | an explicit copy to `OneDrive-ReykjavikUniversity`, which is RU's own tenancy |
| **Canvas token** | environment variable, or `config.json` which is gitignored |

The separation is the point. Student names and engagement scores are personal
data held at an EEA institution, so the fewer places they exist the better.
Code can live anywhere; the data lives here and in RU's OneDrive, and nowhere
else. Nothing syncs student data to a personal account by accident.

## Setup

Create a Canvas token at **Account → Settings → New Access Token**, then:

```sh
cp config.example.json config.json      # fill in canvas_host
export CANVAS_TOKEN='...'               # paste the token

python3 scripts/fetch_roster.py courses # prints your course ids
# put the right id into config.json as canvas_course_id

python3 scripts/fetch_roster.py roster  # writes data/roster.json
```

Re-run the last command whenever enrollment changes. It prints what changed:

```
Wrote data/roster.json (90 students).
  + Kári Helgason
  - Telma Arnardóttir
```

Standard library only — nothing to install, runs on the system Python.

## How a week runs

1. Students pick cards; the card is the group number.
2. Each TA opens the app on their phone and works through their 15 groups:
   tap the students at the table, then Below / Expected / Above on each of the
   engagement factors. **No network needed** — everything is recorded on the
   device.
3. After the session each TA exports; the exports are merged here into one
   file per week.
4. Anyone unassigned at the end of a session was absent. Attendance is a
   by-product, not a separate chore.

Because the two TAs own disjoint sets of groups, their records never collide
and merging is concatenation. The one real error case is the same student
tapped into two groups; the app flags it in the session summary and the merge
step flags it again.

## Status

Recording a session works end to end: pull the roster, import it on each
phone, record a week offline, export it. What is still missing is everything
after the export — merging the two TAs' files, backing them up, and analysis.

See [TODO.md](TODO.md), which is the single list. Keeping a second copy here
only guarantees the two drift apart.

## Configuration

Engagement factors are configuration, not code — they live in the `CONFIG`
object at the top of the app. Adding a criterion mid-semester is one line, and
old weeks simply have no value for it.

Current factors: participation, preparation, collaboration, progress.
Scale: Below / Expected / Above.

Three levels rather than four is deliberate: fewer options means faster
decisions and better agreement between two raters scoring different groups
against the same standard.
