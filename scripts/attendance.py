#!/usr/bin/env python3
"""Per-student attendance for a teaching day, from a merged membership.csv.

Standard library only, matching the rest of scripts/. Reads the output of
merge_exports.py -- run that first.

Why this is separate from summarize.py
--------------------------------------
They serve the two different records described in "HOFI Measurement Plan":
summarize.py reports the GROUP-level research measures (engagement,
collaboration, self-reliance); this reports the STUDENT-level grading record,
which is attendance. Different unit, different purpose, stored separately --
so keeping them in one script would blur exactly the separation the
measurement design depends on.

What it does about a student recorded in two groups
---------------------------------------------------
Nothing, deliberately, and this is the point of the script.

merge_exports.py flags "same student in more than one group in this block"
because that corrupts GROUP COMPOSITION -- which group had which members --
and so it matters for the research record. It does not matter here. A student
tapped into two groups was still present, once. Attendance is a per-student,
per-half-day fact, so this script aggregates to that grain and the duplicate
dissolves on its own. The duplicate is still REPORTED below, so it never
disappears silently, but it does not need fixing before attendance can be
extracted, and the raw JSON never needs hand-editing.

Grain
-----
One row per student on the roster, one column per (week, half) actually
recorded. Per "HOFI Measurement Plan", the grading tick is per half-day, which
is the grain used here -- not per block and not per group.

A student absent from every block is reported as absent, but read that with
care: it means NOBODY RECORDED THEM, which is only the same as "absent" when
TA coverage was complete. Coverage is printed so that judgement stays visible.

Usage
-----
    python3 scripts/attendance.py                      # data/merged/membership.csv
    python3 scripts/attendance.py path/to/membership.csv
    python3 scripts/attendance.py --out data/attendance-w02.csv
    python3 scripts/attendance.py --exclude-ids 33549  # drop a known bad tap
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = ROOT / "data" / "merged" / "membership.csv"
DEFAULT_ROSTER = ROOT / "data" / "roster.json"
DEFAULT_ELSEWHERE = ROOT / "data" / "graded-elsewhere.txt"


def load_roster(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    students = raw if isinstance(raw, list) else raw.get("students", raw)
    return [{"id": str(s["id"]), "name": s.get("name", "")} for s in students]


def load_graded_elsewhere(path: Path | None) -> dict[str, str]:
    """Students whose participation is graded by hand, by someone else.

    One Canvas id per line, optionally followed by whitespace and the name;
    '#' starts a comment. Returns {id: name}. A missing file means nobody.

    The Akureyri cohort is the case: Óli records their attendance there and
    enters their grades himself. They are on the roster (see fetch_roster.py:
    everyone is, on purpose) and never appear in a Reykjavík block, so without
    this list every import would score them 0 -- and an import that scores a
    student 0 overwrites the 1 Óli has already entered.
    """
    if not path or not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        sid, _, name = line.partition(" ")
        out[sid.strip()] = name.strip()
    return out


def write_canvas(path: Path, roster: list[dict], score_of, *, template: Path | None,
                 assignment: str, assignment_id: str | None, points: str,
                 omit: dict[str, str] | None = None) -> None:
    """Write a Canvas gradebook import CSV with one score column.

    score_of(student_id) -> the string to put in the cell. Shared with
    combine_attendance.py, which scores 0 / 0.5 / 1 rather than 0 / 1.

    Canvas matches students on the ID column, which is the Canvas user id --
    the same id fetch_roster.py stores, so no name matching is needed and the
    mojibake that afflicts Icelandic names in Canvas exports never arises.

    A student in `omit` gets NO ROW, not a blank cell. An empty cell in a
    Canvas import is not a no-op: against an existing grade it reads as a
    change to no grade, and Canvas applies it (see takeaway_grades.py for the
    day that was learned). Leaving the row out is the only form Canvas cannot
    misread, and it is what "leave their grade untouched" has to mean.
    """
    header = f"{assignment} ({assignment_id})" if assignment_id else assignment
    path.parent.mkdir(parents=True, exist_ok=True)
    known = {s["id"] for s in roster}
    omit = omit or {}
    left_out: list[tuple[str, str]] = []

    if template:
        # Copy identity columns straight out of Canvas's own export. Canvas matches
        # on ID, but carrying Student/SIS/Section through unchanged means the file
        # cannot disagree with Canvas about who is enrolled, and it makes the import
        # preview readable. The Test Student is Canvas's own fixture, never a person.
        src = list(csv.reader(template.open(newline="", encoding="utf-8")))
        ident = src[0][:5]
        body = [r for r in src[2:] if r and r[1].strip() and "student, Test" not in r[0]]
        skipped = [r for r in src[2:] if r and "student, Test" in r[0]]
        missing = [r for r in body if r[1] not in known]
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(ident + [header])
            w.writerow(["    Points Possible", "", "", "", "", points])
            for r in body:
                if r[1] in omit:
                    left_out.append((r[1], r[0]))
                    continue
                w.writerow(r[:5] + [score_of(r[1]) if r[1] in known else "0"])
        print(f"Wrote {path}  ({len(body) - len(left_out)} students, from Canvas export)")
        if skipped:
            print(f"  dropped Canvas Test Student ({len(skipped)} row)")
        if missing:
            print(f"  ! {len(missing)} in Canvas but not on our roster -- scored 0:")
            for r in missing:
                print(f"      {r[1]}  {r[0]}")
    else:
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Student", "ID", "SIS User ID", "SIS Login ID", "Section", header])
            w.writerow(["    Points Possible", "", "", "", "", points])
            for s in sorted(roster, key=lambda x: x["name"]):
                if s["id"] in omit:
                    left_out.append((s["id"], s["name"]))
                    continue
                w.writerow([s["name"], s["id"], "", "", "", score_of(s["id"])])
        print(f"Wrote {path}  (Canvas gradebook import)")
    if left_out:
        print(f"  left OUT of the file, grade untouched -- graded by hand elsewhere"
              f" ({len(left_out)}):")
        for sid, name in sorted(left_out, key=lambda x: x[1]):
            print(f"      {sid}  {name}")
    unseen = [(sid, name) for sid, name in omit.items()
              if sid not in {i for i, _ in left_out}]
    if unseen:
        print(f"  ! {len(unseen)} on the graded-elsewhere list but not in this file's"
              " roster (dropped the course, or a wrong id?):")
        for sid, name in unseen:
            print(f"      {sid}  {name}")
    if not assignment_id:
        print("  ! No --assignment-id given. Canvas will CREATE A NEW assignment"
              f"\n    called {assignment!r} instead of filling the existing one."
              "\n    Get the id from the assignment URL and re-run before importing.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("membership", nargs="?", type=Path, default=DEFAULT_IN)
    ap.add_argument("--roster", type=Path, default=DEFAULT_ROSTER)
    ap.add_argument("--out", type=Path, help="write CSV here (default: stdout summary only)")
    ap.add_argument("--week", help="only this week, e.g. 2")
    ap.add_argument("--half", choices=["AM","PM"],
                    help="only this half-day. Use when attendance is taken from one "
                         "block rather than the whole day -- e.g. week 2, where the "
                         "morning was well covered and the afternoon was not.")
    ap.add_argument("--exclude-ids", nargs="*", default=[],
                    help="student ids to drop entirely, e.g. a mis-tap on a similar name")
    ap.add_argument("--canvas", type=Path, metavar="FILE",
                    help="also write a Canvas gradebook import CSV here")
    ap.add_argument("--canvas-template", type=Path, metavar="EXPORT",
                    help="a gradebook CSV exported from Canvas. Identity columns are copied "
                         "from it verbatim and Canvas's Test Student is dropped, so the import "
                         "cannot drift from what Canvas actually holds. Strongly preferred.")
    ap.add_argument("--assignment", default="Participation",
                    help="Canvas assignment name for the --canvas column header")
    ap.add_argument("--assignment-id", default=None,
                    help="Canvas assignment id. WITHOUT this, Canvas CREATES A NEW "
                         "assignment on import rather than filling the existing one. "
                         "Find it in the assignment's URL: /assignments/<id>")
    ap.add_argument("--graded-elsewhere", type=Path, default=DEFAULT_ELSEWHERE, metavar="FILE",
                    help="students graded by hand by someone else (Akureyri); their rows "
                         "are LEFT OUT of the Canvas file so their grade is untouched "
                         f"(default {DEFAULT_ELSEWHERE.relative_to(ROOT)} if it exists)")
    ap.add_argument("--points", default="1",
                    help="value written for a present student (default 1); absent gets 0")
    a = ap.parse_args()

    if not a.membership.exists():
        sys.exit(f"attendance: no such file: {a.membership} -- run merge_exports.py first")

    rows = list(csv.DictReader(a.membership.open(newline="", encoding="utf-8")))
    if a.week:
        rows = [r for r in rows if r["week"] == str(a.week)]
    if a.half:
        rows = [r for r in rows if r["half"] == a.half]
    if not rows:
        sys.exit(f"attendance: nothing left after --week/--half filter")
    excluded = set(a.exclude_ids)
    dropped = [r for r in rows if r["student_id"] in excluded]
    rows = [r for r in rows if r["student_id"] not in excluded]

    roster = load_roster(a.roster)
    known = {s["id"] for s in roster}

    # (week, half) -> set of student ids seen; that is the grading grain.
    halves: dict[tuple, set] = defaultdict(set)
    # Duplicates are counted per BLOCK, not per half-day, matching
    # merge_exports.py. A half-day holds several blocks and a student legitimately
    # appears in more than one of them -- notably in a block recorded before the
    # cohort group was set, and then again in their real cohort. Aggregating
    # duplicates at half-day grain reports all of those as errors, which they are not.
    tapped: dict[tuple, set] = defaultdict(set)
    names: dict[str, str] = {}
    for r in rows:
        key = (r["week"], r["half"])
        halves[key].add(r["student_id"])
        block = (r["week"], r["half"], r["condition"], r["cohort_group"])
        tapped[block + (r["student_id"],)].add(r["group"])
        names.setdefault(r["student_id"], r["student_name"])

    half_keys = sorted(halves)
    if not half_keys:
        sys.exit("attendance: no rows found")

    # ---- report ----------------------------------------------------------
    scope = " ".join(x for x in [f"week {a.week}" if a.week else "", a.half or ""] if x)
    print(f"Attendance from {a.membership}" + (f"   [{scope} only]" if scope else ""))
    print(f"Roster: {len(roster)} students\n")

    for k in half_keys:
        seen = halves[k]
        off = seen - known
        print(f"  week {k[0]} {k[1]}: {len(seen)} recorded present"
              + (f"  ({len(off)} not on the roster)" if off else ""))
    print()

    seen_any = set().union(*halves.values())
    print(f"  present in at least one half-day: {len(seen_any)}")
    print(f"  never recorded:                   {len(known - seen_any)}")

    if dropped:
        print(f"\n  excluded by --exclude-ids ({len(dropped)} row(s)):")
        for r in dropped:
            print(f"    {r['student_id']}  {r['student_name']}  (group {r['group']}, {r['ta']})")

    dups = {k: g for k, g in tapped.items() if len(g) > 1}
    if dups:
        print(f"\n  recorded in more than one group ({len(dups)}) --"
              " does not affect attendance, listed so it is not lost:")
        for (wk, half, cond, cohort, sid), groups in sorted(dups.items()):
            where = f"week {wk} {half} {cond}" + (f" cohort {cohort}" if cohort else "")
            print(f"    {where}: {names.get(sid, sid)} ({sid}) in groups {', '.join(sorted(groups))}")

    off_roster = seen_any - known
    if off_roster:
        print(f"\n  recorded but NOT on the roster ({len(off_roster)}) -- check for a late joiner:")
        for sid in sorted(off_roster):
            print(f"    {sid}  {names.get(sid, '?')}")

    print("\n  'never recorded' means nobody tapped them in. That is only the same as"
          "\n  'absent' if TA coverage was complete for every block that half-day.")

    # ---- csv -------------------------------------------------------------
    if a.out:
        cols = [f"w{k[0]}-{k[1]}" for k in half_keys]
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["student_id", "student_name"] + cols + ["present_any"])
            for s in sorted(roster, key=lambda x: x["name"]):
                marks = ["present" if s["id"] in halves[k] else "absent" for k in half_keys]
                w.writerow([s["id"], s["name"]] + marks
                           + ["present" if s["id"] in seen_any else "absent"])
            for sid in sorted(off_roster):
                marks = ["present" if sid in halves[k] else "absent" for k in half_keys]
                w.writerow([sid, names.get(sid, "") + "  [NOT ON ROSTER]"] + marks + ["present"])
        print(f"\nWrote {a.out}")

    # ---- canvas gradebook import ----------------------------------------
    if a.canvas:
        write_canvas(a.canvas, roster, lambda sid: a.points if sid in seen_any else "0",
                     template=a.canvas_template, assignment=a.assignment,
                     assignment_id=a.assignment_id, points=a.points,
                     omit=load_graded_elsewhere(a.graded_elsewhere))


if __name__ == "__main__":
    main()
