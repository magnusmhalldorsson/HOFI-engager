#!/usr/bin/env python3
"""Merge TAs' exported session recordings into one dataset per block.

Standard library only, matching fetch_roster.py.

Why this exists
----------------
Each TA's export is a full snapshot of everything currently on their phone --
not a diff, and not scoped to what THEY were responsible for. Coverage between
TAs may be disjoint (they split the numbered table-groups) or may deliberately
overlap (a calibration week, both TAs rating the same groups so inter-rater
agreement can be checked). The export format cannot tell these apart; this
script has to.

Five problems this solves, none of them solvable by a single phone alone:

  1. Which file wins, when one TA exported more than once.
  2. Split coverage -- different group numbers, same block: a plain union.
  3. Deliberate overlap -- same group numbers, same block, two raters: BOTH
     records are kept (never averaged), and a first-pass agreement figure is
     reported. See the "agreement statistic" note below -- this is provisional.
  4. Accidental cross-device duplication -- the same student tapped into two
     DIFFERENT group numbers by two different TAs. Invisible to either phone;
     only visible once both exports are on the same machine.
  5. Recomputing "not seen" from the union of everyone actually recorded. Any
     single export's own not_seen field is wrong whenever coverage is split,
     because it was computed from only what that one phone saw.

Usage
-----
    python3 scripts/merge_exports.py

With no arguments, reads every .json file the TAs have uploaded to the shared
OneDrive folder (see DEFAULT_EXPORTS_DIR below). Pass explicit paths instead
to merge a specific subset, or exports that live somewhere else:

    python3 scripts/merge_exports.py data/exports/*.json

Reads data/roster.json for the full student population (override with
--roster). Writes into data/merged/ by default (override with --out) --
merged output stays local; only the raw per-TA exports live in OneDrive.

    data/merged/blocks.json      canonical per-block record, issues included
    data/merged/groups.csv       one row per (block, group, rater)
    data/merged/membership.csv   one row per (block, group, rater, student)

Reads data/corrections.csv if present (override with --corrections); see below.

Nothing here is committed to git -- data/ is gitignored entirely, same as the
roster and the raw exports.

Corrections: the raw export is never edited
--------------------------------------------
A TA tapping the wrong student -- the other Pétur, the other Bjarki -- is a
fact about the recording, and the export that holds it is the primary record.
It is not hand-edited. Instead data/corrections.csv lists each known mis-tap
(block, group, which TA, wrong id, right id, why, when) and this script
applies it while merging, prints what it applied, and writes the list into
blocks.json. A correction that matches nothing any more is reported, not
ignored, so the file cannot drift from the exports it corrects.

The first entry, 2026-09-14: week 4 AM, cohort 2, group B4, María tapped
Pétur Jónsson for Pétur Óli Ágústsson. Found because Pétur Jónsson then
appeared in both cohort groups, which is the check below.

A student in both cohort groups is a mis-tap
--------------------------------------------
The two cohort groups of a half-day are complementary halves of the room, so
one student cannot be in both. Per-block duplicate detection (problem 4 above)
cannot see this, because the two taps are in two different blocks. This is
checked across blocks, per (week, half), counting only NAMED cohort groups: a
block recorded before the cohort was set (cohort_group empty) plus the real
one is the legitimate case attendance.py describes, and is not flagged.

Still open, deliberately not decided by this script
-----------------------------------------------------
- The agreement figure below is plain percent-exact-match on an ordinal
  3-point scale. That is fine for a first look at a dry run, but the real
  analysis wants a weighted statistic (e.g. quadratic-weighted kappa) that
  treats a Below/Above disagreement as worse than a Below/Expected one. Not
  implemented here -- do it in whatever stats environment the actual analysis
  runs in, using groups.csv as the input.
- Whether an overlap was a PLANNED calibration week or an accidental double
  entry is not something the data can answer by itself. Once the sealed
  weekly TC/OC allocation exists (see TODO.md), it should also carry which
  weeks are calibration weeks, and this script should check overlaps found
  against that schedule rather than just reporting all of them undifferentiated.
"""

import argparse
import csv
import difflib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROSTER = ROOT / "data" / "roster.json"
DEFAULT_OUT = ROOT / "data" / "merged"
DEFAULT_CORRECTIONS = ROOT / "data" / "corrections.csv"
CORRECTION_FIELDS = ["block_id", "group", "ta", "wrong_id", "right_id", "reason", "date"]

# Where the TAs' phones actually upload to -- the shared folder on RU's
# OneDrive, synced locally by the OneDrive desktop client. Outside the repo
# entirely (it lives under the user's home directory, not ROOT), same as the
# roster and every other place real student data touches disk.
DEFAULT_EXPORTS_DIR = (
    Path.home() / "Library" / "CloudStorage" / "OneDrive-ReykjavikUniversity"
    / "HOFI26" / "Uploads"
)

RATING_KEYS = ["engagement", "collaboration", "selfReliance"]


RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9"]


def group_sort_key(g):
    """Sort card groups in draw order -- reds A..9, then blacks A..9.

    Plain lexicographic order would interleave them as B7, R2, RA, which is
    not how the cards sit on the table. Blocks recorded under the old numeric
    scheme sort ahead of any card, by number.
    """
    g = str(g)
    if g[:1] in ("R", "B") and g[1:] in RANKS:
        return (1, 0 if g[0] == "R" else 1, RANKS.index(g[1:]))
    try:
        return (0, 0, int(g))
    except ValueError:
        return (2, 0, 0)


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError) as err:
        sys.exit("Could not read {}: {}".format(path, err))


def load_roster(path):
    data = load_json(path)
    return {s["id"]: s["name"] for s in data.get("students", [])}


def pick_authoritative(files, union=False):
    """One export per TA: the newest, since each export is a full snapshot.

    Warns if an older file for the same TA has a block the newest one lacks --
    that would mean data loss (phone wiped/reset between exports), not a
    normal supersession, and is worth a human looking at rather than silently
    discarding.
    """
    by_ta = defaultdict(list)
    for path in files:
        data = load_json(path)
        for field in ("ta", "exported", "blocks"):
            if field not in data:
                sys.exit("{}: missing '{}' -- not a valid export?".format(path, field))
        by_ta[data["ta"]].append((data["exported"], path, data))

    chosen = {}
    warnings = []
    for ta, entries in by_ta.items():
        entries.sort(key=lambda e: e[0], reverse=True)
        newest = entries[0]
        newest_blocks = {b["block_id"] for b in newest[2]["blocks"]}

        if union:
            # One TA's blocks can end up split across two devices -- two phones, or
            # one phone and a second browser -- and then no single export is complete.
            # Union them, newest export winning any block recorded in more than one.
            merged, source_of = {}, {}
            for exported, path, data in reversed(entries):        # oldest first
                for b in data["blocks"]:
                    merged[b["block_id"]] = b
                    source_of[b["block_id"]] = path
            data = dict(newest[2]); data["blocks"] = [merged[k] for k in sorted(merged)]
            extra = sorted(set(merged) - newest_blocks)
            chosen[ta] = {"path": newest[1], "data": data,
                          "union_of": sorted({str(p) for p in source_of.values()})}
            if extra:
                warnings.append(
                    "{}: --union recovered block(s) {} that the newest export {} "
                    "does not contain.".format(ta, extra, newest[1].name))
            continue

        chosen[ta] = {"path": newest[1], "data": newest[2]}
        for exported, path, data in entries[1:]:
            missing = {b["block_id"] for b in data["blocks"]} - newest_blocks
            if missing:
                warnings.append(
                    "{}: {} has block(s) {} not present in the newer export {} "
                    "for the same TA -- possible data loss, check by hand. "
                    "Re-run with --union to keep both.".format(ta, path, sorted(missing), newest[1])
                )

    # Loose typo check across the TA names actually seen -- three real TAs
    # this semester, so a near-miss ("Sara" vs "Saraa") is worth a nudge.
    names = list(chosen)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if difflib.SequenceMatcher(None, a, b).ratio() > 0.8:
                warnings.append(
                    "TA names {!r} and {!r} are suspiciously similar -- "
                    "same person, typo'd twice?".format(a, b)
                )

    return chosen, warnings


def load_corrections(path):
    """data/corrections.csv -> list of dicts, or [] if there is no such file.

    Columns: block_id, group, ta, wrong_id, right_id, reason, date. `ta` may be
    blank to mean whichever TA recorded that group. Every row must say why.
    """
    if not path or not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    missing = [f for f in CORRECTION_FIELDS if rows and f not in rows[0]]
    if missing:
        sys.exit("{}: missing column(s) {} -- expected {}".format(
            path, ", ".join(missing), ", ".join(CORRECTION_FIELDS)))
    out = []
    for i, r in enumerate(rows, start=2):
        r = {k: (v or "").strip() for k, v in r.items()}
        if not r["block_id"]:
            continue
        for f in ("group", "wrong_id", "right_id", "reason"):
            if not r[f]:
                sys.exit("{} line {}: '{}' is empty -- a correction has to say what and why".format(
                    path, i, f))
        out.append(r)
    return out


def apply_corrections(chosen, corrections, roster):
    """Swap wrong_id for right_id in the matching group(s), in memory only.

    Returns (applied, stale): human-readable lines for what changed, and the
    corrections that matched nothing -- which means the exports have changed
    under them, or the row is wrong, and either way somebody should look.
    """
    applied, stale = [], []
    for c in corrections:
        hit = False
        for ta, entry in chosen.items():
            if c["ta"] and c["ta"] != ta:
                continue
            for b in entry["data"]["blocks"]:
                if b["block_id"] != c["block_id"]:
                    continue
                for g in b["groups"]:
                    if str(g["group"]) != c["group"] or c["wrong_id"] not in g["students"]:
                        continue
                    g["students"] = [c["right_id"] if x == c["wrong_id"] else x
                                     for x in g["students"]]
                    if c["wrong_id"] in g.get("no_part", []):
                        g["no_part"] = [c["right_id"] if x == c["wrong_id"] else x
                                        for x in g["no_part"]]
                    hit = True
                    applied.append("{} group {} ({}): {} -> {}  [{}{}]".format(
                        c["block_id"], c["group"], ta,
                        roster.get(c["wrong_id"], c["wrong_id"]),
                        roster.get(c["right_id"], c["right_id"]),
                        c["reason"], ", " + c["date"] if c["date"] else ""))
        if not hit:
            stale.append("{} group {}{}: {} not found there -- correction did nothing".format(
                c["block_id"], c["group"], " (" + c["ta"] + ")" if c["ta"] else "",
                roster.get(c["wrong_id"], c["wrong_id"])))
    return applied, stale


def merge(chosen, roster):
    """Combine the authoritative per-TA data into one record per block_id."""
    by_block = defaultdict(lambda: {"week": None, "half": None, "cohort_group": None,
                                     "conditions": {}, "groups": defaultdict(list)})

    for ta, entry in chosen.items():
        for b in entry["data"]["blocks"]:
            rec = by_block[b["block_id"]]
            rec["week"] = b["week"]
            rec["half"] = b["half"]
            # cohort_group (Group 1/2 within a TC session) is baked into
            # block_id itself, so every TA recording this block_id necessarily
            # agrees on it -- nothing to reconcile, unlike condition below.
            rec["cohort_group"] = b.get("cohort_group")
            rec["conditions"][ta] = b["condition"]
            for g in b["groups"]:
                rec["groups"][g["group"]].append({
                    "ta": ta,
                    "students": g["students"],
                    "no_part": g.get("no_part", []),
                    "scores": g.get("scores", {}),
                    "progress": g.get("progress"),
                })

    blocks_out = []
    agreement_out = []
    global_issues = []

    for block_id in sorted(by_block):
        rec = by_block[block_id]
        issues = []

        conditions = rec["conditions"]
        distinct = set(conditions.values())
        if len(distinct) > 1:
            condition = None
            issues.append(
                "TAs disagree on the pedagogy for this block: " +
                ", ".join("{}={}".format(ta, c) for ta, c in sorted(conditions.items())) +
                " -- resolve by hand before using this block."
            )
        else:
            condition = next(iter(distinct))

        groups_out = []
        present = set()
        # student_id -> list of (ta, group_number), across ALL groups in this
        # block, to catch a student placed under two different numbers by two
        # different TAs -- the case neither phone alone can see.
        student_locations = defaultdict(list)

        for gnum in sorted(rec["groups"], key=group_sort_key):
            ratings = rec["groups"][gnum]
            groups_out.append({"group": gnum, "ratings": ratings})
            for r in ratings:
                for sid in r["students"]:
                    present.add(sid)
                    student_locations[sid].append((r["ta"], gnum))

            if len(ratings) > 1:
                for i in range(len(ratings)):
                    for j in range(i + 1, len(ratings)):
                        a, b = ratings[i], ratings[j]
                        row = {
                            "block_id": block_id, "group": gnum,
                            "rater_a": a["ta"], "rater_b": b["ta"],
                        }
                        for key in RATING_KEYS:
                            va, vb = a["scores"].get(key), b["scores"].get(key)
                            row[key + "_a"] = va
                            row[key + "_b"] = vb
                            row[key + "_match"] = (va == vb) if va and vb else None
                        agreement_out.append(row)
                        if a["progress"] != b["progress"]:
                            issues.append(
                                "Group {}: {} and {} logged different progress "
                                "({!r} vs {!r}) for what should be the same "
                                "group -- progress is meant to be observed, not "
                                "judged, so a mismatch is more likely an error "
                                "than a real disagreement.".format(
                                    gnum, a["ta"], b["ta"], a["progress"], b["progress"]))

        for sid, locations in student_locations.items():
            distinct_groups = {g for _, g in locations}
            if len(distinct_groups) > 1:
                name = roster.get(sid, sid)
                issues.append(
                    "{} recorded in more than one group in this block: {} "
                    "-- fix before analysis; this cannot be seen from either "
                    "phone alone.".format(
                        name, ", ".join("group {} ({})".format(g, ta) for ta, g in locations)))

        not_seen = sorted(set(roster) - present, key=lambda sid: roster.get(sid, sid))

        blocks_out.append({
            "block_id": block_id, "week": rec["week"], "half": rec["half"],
            "cohort_group": rec["cohort_group"],
            "condition": condition, "raters": sorted(rec["conditions"]),
            "groups": groups_out,
            "present": sorted(present), "not_seen": not_seen,
            "issues": issues,
        })
        global_issues.extend("{}: {}".format(block_id, i) for i in issues)

    # A student in two NAMED cohort groups of the same half-day. Only visible
    # across blocks, so it lives here rather than in the per-block loop.
    where = defaultdict(lambda: defaultdict(list))   # (week, half) -> sid -> [(cg, group, ta)]
    for b in blocks_out:
        if not b["cohort_group"]:
            continue
        for g in b["groups"]:
            for r in g["ratings"]:
                for sid in r["students"]:
                    where[(b["week"], b["half"])][sid].append((b["cohort_group"], g["group"], r["ta"]))
    for (week, half), students in sorted(where.items()):
        for sid, spots in sorted(students.items(), key=lambda kv: roster.get(kv[0], kv[0])):
            if len({cg for cg, _, _ in spots}) > 1:
                global_issues.append(
                    "w{:02d}-{}: {} recorded in both cohort groups of the same half-day: {} "
                    "-- the cohort groups are complementary halves of the room, so one of "
                    "these is a mis-tap, most likely on a similar name. Fix via "
                    "data/corrections.csv.".format(
                        int(week), half, roster.get(sid, sid),
                        ", ".join("G{} group {} ({})".format(cg, g, ta) for cg, g, ta in spots)))

    return blocks_out, agreement_out, global_issues


def write_outputs(blocks, agreement, issues, chosen, roster, warnings, out_dir,
                  corrections_applied=()):
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "blocks.json", "w", encoding="utf-8") as fh:
        json.dump({
            "source_files": {ta: str(e["path"]) for ta, e in chosen.items()},
            "roster_size": len(roster),
            "load_warnings": warnings,
            "corrections_applied": list(corrections_applied),
            "blocks": blocks,
            "agreement": agreement,
            "issues": issues,
        }, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    with open(out_dir / "groups.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["week", "half", "condition", "cohort_group", "group", "ta",
                    "engagement", "collaboration", "self_reliance", "progress",
                    "n_students", "n_flagged_no_part"])
        for b in blocks:
            for g in b["groups"]:
                for r in g["ratings"]:
                    w.writerow([
                        b["week"], b["half"], b["condition"], b["cohort_group"] or "",
                        g["group"], r["ta"],
                        r["scores"].get("engagement", ""),
                        r["scores"].get("collaboration", ""),
                        # schema <5 called this stopThinking and ran the scale the other way;
                        # it is read here only so old exports still parse, never merged with new.
                        r["scores"].get("selfReliance", r["scores"].get("stopThinking", "")),
                        r["progress"] or "",
                        len(r["students"]), len(r["no_part"]),
                    ])

    with open(out_dir / "membership.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["week", "half", "condition", "cohort_group", "group", "ta",
                    "student_id", "student_name", "no_part"])
        for b in blocks:
            for g in b["groups"]:
                for r in g["ratings"]:
                    for sid in r["students"]:
                        w.writerow([
                            b["week"], b["half"], b["condition"], b["cohort_group"] or "",
                            g["group"], r["ta"],
                            sid, roster.get(sid, ""), sid in r["no_part"],
                        ])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exports", nargs="*",
                    help="export JSON files, one per TA (default: everything "
                         "currently in the shared OneDrive Uploads folder)")
    ap.add_argument("--roster", default=str(DEFAULT_ROSTER), help="path to roster.json")
    ap.add_argument("--union", action="store_true",
                    help="keep every block a TA recorded, not just those in their newest "
                         "export -- for when one TA's work is split across two devices")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="output directory")
    ap.add_argument("--corrections", default=str(DEFAULT_CORRECTIONS),
                    help="known mis-taps to apply while merging (default data/corrections.csv "
                         "if it exists; pass an empty string to apply none)")
    args = ap.parse_args()

    if args.exports:
        paths = [Path(p) for p in args.exports]
    else:
        if not DEFAULT_EXPORTS_DIR.is_dir():
            sys.exit(
                "No paths given, and the default OneDrive folder isn't there:\n"
                "    {}\n"
                "Is the OneDrive desktop client running and that folder synced? "
                "Or pass export paths explicitly.".format(DEFAULT_EXPORTS_DIR)
            )
        paths = sorted(DEFAULT_EXPORTS_DIR.glob("*.json"))
        if not paths:
            sys.exit("No .json files found in {}.".format(DEFAULT_EXPORTS_DIR))

    roster = load_roster(Path(args.roster))
    chosen, load_warnings = pick_authoritative(paths, union=args.union)
    corrections = load_corrections(Path(args.corrections)) if args.corrections else []
    applied, stale = apply_corrections(chosen, corrections, roster)
    load_warnings = list(load_warnings) + stale
    blocks, agreement, issues = merge(chosen, roster)
    write_outputs(blocks, agreement, issues, chosen, roster, load_warnings, Path(args.out),
                  corrections_applied=applied)

    print("Merged {} TA(s) across {} block(s) -> {}".format(len(chosen), len(blocks), args.out))
    for ta, entry in sorted(chosen.items()):
        print("  {} <- {}".format(ta, entry["path"]))

    if applied:
        print("\nCorrections applied ({}), from {}:".format(len(applied), args.corrections))
        for line in applied:
            print("  * " + line)

    if load_warnings:
        print("\nLoad warnings:")
        for w in load_warnings:
            print("  ! " + w)

    if issues:
        print("\nIssues found ({}):".format(len(issues)))
        for i in issues:
            print("  ! " + i)
    else:
        print("\nNo issues found.")

    if agreement:
        n = len(agreement)
        for key in RATING_KEYS:
            matches = sum(1 for r in agreement if r[key + "_match"])
            scored = sum(1 for r in agreement if r[key + "_match"] is not None)
            if scored:
                print("Provisional agreement on {}: {}/{} exact ({:.0%}) "
                      "-- percent-match only; see the script docstring "
                      "for why this is not the final statistic.".format(
                          key, matches, scored, matches / scored))


if __name__ == "__main__":
    main()
