#!/usr/bin/env python3
"""Combine Challenge-Lab and Skill-Lab attendance into one participation score.

Standard library only, matching the rest of scripts/.

The scheme (from week 4 on)
---------------------------
A half-day earns 0.5 when the student attended BOTH labs that half-day: the
Challenge Lab, recorded by the TAs in the engagement app and extracted by
attendance.py, and the Skill Lab, ticked by hand in the Drive sheet
"Student Admin / Attendance / Skill Lab Attendance". Two half-days, so the
score is 0, 0.5 or 1, against a 1-point Canvas assignment.

Skill Lab 1 is the morning, Skill Lab 2 the afternoon. That is not stated in
the sheet; it was confirmed on week 4 by overlap (Skill Lab 2 and the PM
Challenge Lab agreed on all 67 students). If the sheet's columns ever change
meaning, --am-col / --pm-col are there.

Why names, and what can go wrong
--------------------------------
The Skill Lab sheet carries names only, no ids, so it is matched to
data/roster.json by name (NFC-normalised, case-folded, whitespace-collapsed).
Every way that can fail is REPORTED, never silently absorbed:

  * a sheet name that matches nobody on the roster -- harmless if the row is
    unticked (a student who dropped), a lost mark if it is ticked;
  * a roster student with no row in the sheet at all -- harmless if they were
    not in the Challenge Lab either, but if they WERE, they lose a half-day for
    a clerical reason, which is not what the scheme intends;
  * a spelling that differs only in case or accents, so you can fix the sheet.

The two records disagreeing on a student (in one lab, not the other) is not an
error -- that is the scheme doing its job -- but each case is listed, because
on a single-TA half-day a Challenge-Lab "absent" may mean "not tapped in".

Usage
-----
    python3 scripts/combine_attendance.py --week 4 --skill-lab data/skill-lab-w04.csv \\
        --canvas data/canvas-participation-w04.csv \\
        --canvas-template ~/Downloads/<export>.csv \\
        --assignment "Participation (Week 4)" --assignment-id 112226

Download the sheet as CSV (File > Download > .csv) for --skill-lab. Reads
data/attendance-wNN.csv, so run attendance.py --week NN --out first.
"""
from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from attendance import load_roster, write_canvas  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def norm(name: str) -> str:
    return unicodedata.normalize("NFC", " ".join(name.split())).casefold()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--week", required=True, help="week number, e.g. 4")
    ap.add_argument("--skill-lab", required=True, type=Path, metavar="CSV",
                    help="the Skill Lab Attendance sheet, downloaded as CSV")
    ap.add_argument("--attendance", type=Path, metavar="CSV",
                    help="Challenge-Lab attendance from attendance.py "
                         "(default data/attendance-wNN.csv)")
    ap.add_argument("--roster", type=Path, default=ROOT / "data" / "roster.json")
    ap.add_argument("--name-col", default="Nafn")
    ap.add_argument("--am-col", default="Skill Lab 1")
    ap.add_argument("--pm-col", default="Skill Lab 2")
    ap.add_argument("--out", type=Path, metavar="CSV",
                    help="per-student breakdown (default data/attendance-combined-wNN.csv)")
    ap.add_argument("--canvas", type=Path, metavar="FILE",
                    help="also write a Canvas gradebook import CSV here")
    ap.add_argument("--canvas-template", type=Path, metavar="EXPORT",
                    help="a gradebook CSV exported from Canvas; strongly preferred, "
                         "see attendance.py")
    ap.add_argument("--assignment", default="Participation")
    ap.add_argument("--assignment-id", default=None,
                    help="Canvas assignment id; without it Canvas creates a new assignment")
    a = ap.parse_args()

    wk = str(a.week).lstrip("0") or "0"
    att_path = a.attendance or ROOT / "data" / f"attendance-w{int(wk):02d}.csv"
    out_path = a.out or ROOT / "data" / f"attendance-combined-w{int(wk):02d}.csv"
    for p in (att_path, a.skill_lab, a.roster):
        if not p.exists():
            sys.exit(f"combine_attendance: no such file: {p}")

    roster = load_roster(a.roster)
    by_norm = {norm(s["name"]): s for s in roster}
    am_key, pm_key = f"w{wk}-AM", f"w{wk}-PM"

    # ---- challenge lab (ids) ------------------------------------------
    att = {r["student_id"]: r for r in csv.DictReader(att_path.open(newline="", encoding="utf-8"))}
    for k in (am_key, pm_key):
        if not att or k not in next(iter(att.values())):
            sys.exit(f"combine_attendance: {att_path} has no column {k!r} -- "
                     f"run attendance.py --week {wk} --out {att_path} first")
    ch_am = {sid for sid, r in att.items() if r[am_key] == "present"}
    ch_pm = {sid for sid, r in att.items() if r[pm_key] == "present"}

    # ---- skill lab (names) --------------------------------------------
    with a.skill_lab.open(newline="", encoding="utf-8") as f:
        sheet_rows = [r for r in csv.DictReader(f)
                      if r.get(a.name_col, "").strip()
                      and norm(r[a.name_col]) not in ("samtals", "total")]
    for col in (a.name_col, a.am_col, a.pm_col):
        if sheet_rows and col not in sheet_rows[0]:
            sys.exit(f"combine_attendance: sheet has no column {col!r}; "
                     f"columns are {list(sheet_rows[0])}")
    dup_names = [n for n, c in Counter(norm(r[a.name_col]) for r in sheet_rows).items() if c > 1]
    ticked = {r[a.am_col].strip() for r in sheet_rows} | {r[a.pm_col].strip() for r in sheet_rows}

    sk_am: set[str] = set()   # roster ids ticked for the AM skill lab
    sk_pm: set[str] = set()
    unmatched: list[tuple[str, bool]] = []      # (sheet name, was ticked anywhere)
    spelling: list[tuple[str, str]] = []
    seen_norms: set[str] = set()
    for r in sheet_rows:
        raw = r[a.name_col].strip()
        n = norm(raw)
        seen_norms.add(n)
        s = by_norm.get(n)
        t_am, t_pm = bool(r[a.am_col].strip()), bool(r[a.pm_col].strip())
        if s is None:
            unmatched.append((raw, t_am or t_pm))
            continue
        if raw != s["name"]:
            spelling.append((raw, s["name"]))
        if t_am:
            sk_am.add(s["id"])
        if t_pm:
            sk_pm.add(s["id"])
    no_row = [s for s in roster if norm(s["name"]) not in seen_norms]

    # ---- score ---------------------------------------------------------
    half_am = ch_am & sk_am
    half_pm = ch_pm & sk_pm
    score = {s["id"]: (0.5 if s["id"] in half_am else 0) + (0.5 if s["id"] in half_pm else 0)
             for s in roster}

    # ---- report --------------------------------------------------------
    print(f"Combined participation, week {wk}")
    print(f"  Challenge Lab: {att_path}   Skill Lab: {a.skill_lab}")
    print(f"  Roster {len(roster)}; sheet rows {len(sheet_rows)}; tick marks used: "
          + ", ".join(repr(v) for v in sorted(ticked) if v) + "\n")

    print(f"  {'':14s}{'Challenge':>10s}{'Skill':>8s}{'both':>8s}")
    print(f"  {'AM':14s}{len(ch_am):>10d}{len(sk_am):>8d}{len(half_am):>8d}")
    print(f"  {'PM':14s}{len(ch_pm):>10d}{len(sk_pm):>8d}{len(half_pm):>8d}")
    dist = Counter(score.values())
    print(f"\n  score 1: {dist.get(1.0, 0)}   score 0.5: {dist.get(0.5, 0)}   score 0: {dist.get(0, 0)}")

    problems = 0
    print("\nName matching")
    if dup_names:
        problems += 1
        print(f"  ! sheet lists the same name more than once: {', '.join(dup_names)}")
    lost = [(n, t) for n, t in unmatched if t]
    dropped = [(n, t) for n, t in unmatched if not t]
    if lost:
        problems += 1
        print(f"  ! {len(lost)} sheet name(s) TICKED but matching nobody on the roster --"
              " those marks are LOST until the name is fixed:")
        for n, _ in lost:
            print(f"      {n}")
    if dropped:
        print(f"  {len(dropped)} sheet name(s) not on the roster, unticked (probably dropped;"
              " remove from the sheet):")
        for n, _ in dropped:
            print(f"      {n}")
    hurt = [s for s in no_row if s["id"] in ch_am or s["id"] in ch_pm]
    if hurt:
        problems += 1
        print(f"  ! {len(hurt)} roster student(s) with NO ROW in the sheet who WERE in a"
              " Challenge Lab -- they lose credit for a clerical reason. Add them to the sheet:")
        for s in hurt:
            print(f"      {s['name']}  ({s['id']})  AM={'present' if s['id'] in ch_am else 'absent'}"
                  f"  PM={'present' if s['id'] in ch_pm else 'absent'}")
    quiet = [s for s in no_row if s not in hurt]
    if quiet:
        print(f"  {len(quiet)} roster student(s) with no row in the sheet, absent from both"
              " Challenge Labs too (no effect this week, but add them so a late joiner is"
              " not invisible):")
        for s in quiet:
            print(f"      {s['name']}")
    if spelling:
        print(f"  {len(spelling)} matched despite a spelling difference (sheet vs roster):")
        for raw, canon in spelling:
            print(f"      {raw!r}  vs  {canon!r}")
    if not (dup_names or unmatched or no_row or spelling):
        print("  every sheet name matches the roster exactly, and vice versa")

    print("\nDisagreements between the two records (not errors; listed so nothing is hidden)")
    def show(label, ch, sk):
        only_ch = sorted(ch - sk, key=lambda i: att[i]["student_name"])
        only_sk = sorted(sk - ch, key=lambda i: att[i]["student_name"])
        for sid in only_ch:
            print(f"  {label}: {att[sid]['student_name']:35s} Challenge Lab yes, Skill Lab no  -> 0")
        for sid in only_sk:
            print(f"  {label}: {att[sid]['student_name']:35s} Skill Lab yes, Challenge Lab no  -> 0")
        return len(only_ch) + len(only_sk)
    n_dis = show("AM", ch_am, sk_am) + show("PM", ch_pm, sk_pm)
    if not n_dis:
        print("  none -- the two records agree on every student")

    # ---- outputs -------------------------------------------------------
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["student_id", "student_name", f"{am_key}-challenge", f"{am_key}-skill",
                    f"{pm_key}-challenge", f"{pm_key}-skill", "score"])
        for s in sorted(roster, key=lambda x: x["name"]):
            i = s["id"]
            w.writerow([i, s["name"],
                        "present" if i in ch_am else "absent", "x" if i in sk_am else "",
                        "present" if i in ch_pm else "absent", "x" if i in sk_pm else "",
                        f"{score[i]:g}"])
    print(f"\nWrote {out_path}")

    if a.canvas:
        write_canvas(a.canvas, roster, lambda sid: f"{score.get(sid, 0):g}",
                     template=a.canvas_template, assignment=a.assignment,
                     assignment_id=a.assignment_id, points="1")
    if problems:
        print(f"\n  {problems} problem(s) above change someone's score. Fix the sheet and re-run"
              " before importing.")


if __name__ == "__main__":
    main()
