#!/usr/bin/env python3
"""Canvas gradebook import for a weekly Takeaway Task: full marks for submitting.

Standard library only, matching the rest of scripts/. Reads Canvas over the
API using the same token as fetch_roster.py; writes a CSV for you to upload at
Canvas > Grades > Import.

Why full marks for submitting
-----------------------------
The Takeaway is a take-home artifact plus two questions, and per "HOFI Dessert
Design" its second question is the meta-skill question -- disclose the AI you
used, say where it was wrong. That only works if answering honestly is free.
So the mark is for handing in, and the answers get summarised back to the room
rather than scored. This script encodes that rule and nothing else; anything
you actually want to read, it points you at instead of judging.

What it does not do
-------------------
It does not write to Canvas. It produces a file you look at and then upload,
because a grade is student-visible the moment it posts and a mistake at this
grain is 90 mistakes. The report it prints is the review step: read the
exceptions, then import.

A student who should not be touched is left OUT OF THE FILE, not left blank
--------------------------------------------------------------------------
An empty cell in a Canvas import is not a no-op. Against an existing grade it
reads as a change to *no grade*, and Canvas applies it: on 2026-09-08 an
import whose only empty cells were the four students already graded 100
deleted those four grades, silently and after they had been posted.

So this script writes a row only for a student who is getting a mark. Anyone
it decides not to grade -- already graded, or did not submit -- is absent from
the file entirely, which is the only form Canvas cannot misread.

`--absent zero` writes 0 for a student who did not submit, matching what
attendance.py does for a missing student; those rows do appear. That is the
right call once a deadline is properly closed and the total needs to be
honest, and the wrong call while late work is still arriving, which for the
Takeaway it usually is.

Students already graded are omitted so an import cannot overwrite and re-post
a grade that is already correct and already seen. `--regrade` includes them.

Identity columns
----------------
Canvas matches an imported row on the `ID` column alone, so by default only
`Student` and `ID` are filled and the SIS columns are left empty -- this repo
asks Canvas for the fields it needs and no more. Pass `--template` with a
gradebook CSV exported from Canvas to copy all five identity columns verbatim
instead; the roster is still taken from the API, so a student who enrolled or
left since that export is handled correctly either way.

Usage
-----
    python3 scripts/takeaway_grades.py --week 2
    python3 scripts/takeaway_grades.py --week 2 --absent zero
    python3 scripts/takeaway_grades.py --week 3 --out /tmp/w3.csv
    python3 scripts/takeaway_grades.py --list          # assignment ids and names
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_roster as canvas  # noqa: E402  -- token, config and paging live there

ROOT = Path(__file__).resolve().parent.parent
IDENT = ["Student", "ID", "SIS User ID", "SIS Login ID", "Section"]


def find_assignment(cfg, tok, week, assignment_id):
    """The Canvas assignment for this week, matched by name unless an id is given."""
    rows = list(canvas.get_pages(
        cfg["canvas_host"], "/courses/{}/assignments".format(canvas.course_ref(cfg)),
        tok, {"per_page": 100}))
    if assignment_id:
        for a in rows:
            if str(a["id"]) == str(assignment_id):
                return a
        sys.exit("takeaway_grades: no assignment {} in this course".format(assignment_id))

    # Canvas names carry stray whitespace often enough that exact matching fails
    # on a name that looks right on screen; compare on the squeezed form.
    want = "takeaway task (week {})".format(week)
    hits = [a for a in rows if " ".join(a["name"].split()).lower() == want]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit("takeaway_grades: no assignment named 'Takeaway Task (Week {})'.\n"
                 "Run with --list to see the names Canvas actually holds."
                 .format(week))
    sys.exit("takeaway_grades: {} assignments named 'Takeaway Task (Week {})' -- "
             "pass --assignment-id".format(len(hits), week))


def active_students(cfg, tok):
    """id -> name for currently enrolled students. Excludes Canvas's Test Student,
    which has a StudentViewEnrollment and so never appears here."""
    rows = list(canvas.get_pages(
        cfg["canvas_host"], "/courses/{}/enrollments".format(canvas.course_ref(cfg)),
        tok, {"per_page": 100, "type[]": "StudentEnrollment", "state[]": "active"}))
    return {str(e["user"]["id"]): e["user"].get("name", "").strip() for e in rows}


def submission_size(sub):
    """Bytes handed in, however it was handed in: uploads, or a text entry."""
    total = sum(a.get("size") or 0 for a in (sub.get("attachments") or []))
    return total or len(sub.get("body") or "")


def template_identity(path):
    """id -> the five identity columns, from a Canvas gradebook export.

    Returns them in the export's own order, which is Canvas's own sort, so a
    file built from a template can be read side by side with the gradebook.
    """
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    if not rows or rows[0][:2] != IDENT[:2]:
        sys.exit("takeaway_grades: {} does not look like a Canvas gradebook export "
                 "(first columns should be Student, ID)".format(path))
    out = {}
    for r in rows[1:]:
        if len(r) >= 5 and r[1].strip().isdigit():
            out[r[1].strip()] = r[:5]
    return out


# Python sorts þ, æ, ö and every accented vowel after z, which scatters a
# class list of Icelandic names. macOS ships no reliable is_IS collation to
# lean on, so the alphabet is spelled out; anything not in it sorts last.
ICELANDIC = "aábcdðeéfghiíjklmnoópqrstuúvwxyýzþæö"


def icelandic_key(name):
    return [(ICELANDIC.index(ch), 0) if ch in ICELANDIC else (len(ICELANDIC), ord(ch))
            for ch in name.lower()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--week", help="course week, e.g. 2")
    ap.add_argument("--assignment-id", help="use this Canvas assignment id instead of "
                                            "matching on the week number")
    ap.add_argument("--list", action="store_true", help="print assignment ids and names, "
                                                        "then stop")
    ap.add_argument("--out", type=Path, help="write here "
                                             "(default: data/canvas-takeaway-wNN.csv)")
    ap.add_argument("--absent", choices=["blank", "zero"], default="blank",
                    help="what to write for a student who did not submit (default blank, "
                         "which changes nothing on import)")
    ap.add_argument("--regrade", action="store_true",
                    help="also write the mark for students already graded, overwriting "
                         "and re-posting their existing grade")
    ap.add_argument("--points", help="mark for a submitting student "
                                     "(default: the assignment's points possible)")
    ap.add_argument("--template", type=Path, metavar="EXPORT",
                    help="a gradebook CSV exported from Canvas; identity columns are "
                         "copied from it verbatim")
    ap.add_argument("--thin", type=int, default=1000, metavar="BYTES",
                    help="report submissions smaller than this for a human look "
                         "(default 1000; 0 disables)")
    a = ap.parse_args()

    cfg = canvas.load_config()
    tok = canvas.token(cfg)
    ref = canvas.course_ref(cfg)

    if a.list:
        for row in canvas.get_pages(cfg["canvas_host"],
                                    "/courses/{}/assignments".format(ref), tok,
                                    {"per_page": 100}):
            print("{:>8}  {:<28}  {}".format(
                row["id"], row.get("name", "?"),
                "{} pts".format(row.get("points_possible"))))
        return

    if not (a.week or a.assignment_id):
        sys.exit("takeaway_grades: give --week N (or --assignment-id), or --list")

    assignment = find_assignment(cfg, tok, a.week, a.assignment_id)
    points = a.points if a.points is not None else _clean(assignment.get("points_possible"))
    header = "{} ({})".format(assignment["name"], assignment["id"])

    enrolled = active_students(cfg, tok)
    subs = {str(s["user_id"]): s for s in canvas.get_pages(
        cfg["canvas_host"],
        "/courses/{}/assignments/{}/submissions".format(ref, assignment["id"]),
        tok, {"per_page": 100})}

    identity = template_identity(a.template) if a.template else {}
    absent_value = "0" if a.absent == "zero" else ""

    # Template order is Canvas's own; without one, collate the names properly.
    if identity:
        order = [sid for sid in identity if sid in enrolled]
        order += sorted((sid for sid in enrolled if sid not in identity),
                        key=lambda s: icelandic_key(enrolled[s]))
    else:
        order = sorted(enrolled, key=lambda s: icelandic_key(enrolled[s]))

    rows, scored, already, absent = [], [], [], []
    late, thin, no_record = [], [], []
    for sid in order:
        name = enrolled[sid]
        sub = subs.get(sid)
        ident = identity.get(sid, [name, sid, "", "", ""])
        if sub is None:
            # An active enrollment with no submission record at all: Canvas
            # normally makes one per student, so this means something is off.
            no_record.append(name)
            continue
        if sub.get("score") is not None and not a.regrade:
            already.append((name, sub["score"]))
        elif sub.get("submitted_at"):
            scored.append(name)
            rows.append(ident + [points])
            if sub.get("late"):
                late.append((name, sub.get("submitted_at"),
                             round((sub.get("seconds_late") or 0) / 86400, 1)))
            size = submission_size(sub)
            if a.thin and size < a.thin:
                thin.append((name, size))
        else:
            absent.append(name)
            if absent_value:
                rows.append(ident + [absent_value])

    if a.out:
        out = a.out
    elif a.week:
        out = ROOT / "data" / "canvas-takeaway-w{:02d}.csv".format(int(a.week))
    else:
        out = ROOT / "data" / "canvas-takeaway-{}.csv".format(assignment["id"])
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(IDENT + [header])
        w.writerow(["    Points Possible", "", "", "", "", points])
        w.writerows(rows)

    print("{}  ({})".format(assignment["name"].strip(), assignment["id"]))
    print("Wrote {}  ({} rows, of {} enrolled)".format(out, len(rows), len(enrolled)))
    print("  {:>3} scored {}".format(len(scored), points))
    print("  {:>3} already graded, not in the file{}".format(
        len(already), " -- use --regrade to overwrite" if already else ""))
    print("  {:>3} did not submit, {}".format(
        len(absent), "written as 0" if absent_value else "not in the file"))

    if late:
        print("\n! {} late, and scored anyway:".format(len(late)))
        for name, when, days in late:
            print("    {:<34} {}  ({} days late)".format(name, when, days))
    if thin:
        print("\n? {} submissions under {} bytes -- worth opening before you import:"
              .format(len(thin), a.thin))
        for name, size in sorted(thin, key=lambda t: t[1]):
            print("    {:<34} {} bytes".format(name, size))
    if no_record:
        print("\n! {} enrolled with no submission record at all, not in the file:"
              .format(len(no_record)))
        for name in no_record:
            print("    {}".format(name))
    stale = [sid for sid in subs if sid not in enrolled and subs[sid].get("submitted_at")]
    if stale:
        print("\n! {} submission(s) from students no longer enrolled, not in the file:"
              .format(len(stale)))
        for sid in stale:
            print("    user {}".format(sid))

    if assignment.get("post_manually"):
        print("\n! This assignment posts grades MANUALLY, so an import is invisible to\n"
              "  students until you post it: Grades > the column's menu > Post grades.")

    print("\nUpload at Canvas > Grades > Import. Every row in the file is a grade to\n"
          "write; a student not in the file is not touched.")


def _clean(points):
    """100.0 -> '100'. Canvas hands back floats; the gradebook reads either, but
    a whole number in the file is what a human comparing it to Canvas expects."""
    if points is None:
        return "100"
    if float(points).is_integer():
        return str(int(points))
    return str(points)


if __name__ == "__main__":
    main()
