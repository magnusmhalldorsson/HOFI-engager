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

Nothing here is committed to git -- data/ is gitignored entirely, same as the
roster and the raw exports.

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

# Where the TAs' phones actually upload to -- the shared folder on RU's
# OneDrive, synced locally by the OneDrive desktop client. Outside the repo
# entirely (it lives under the user's home directory, not ROOT), same as the
# roster and every other place real student data touches disk.
DEFAULT_EXPORTS_DIR = (
    Path.home() / "Library" / "CloudStorage" / "OneDrive-ReykjavikUniversity"
    / "HOFI26" / "Uploads"
)

RATING_KEYS = ["engagement", "collaboration"]


def load_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (ValueError, OSError) as err:
        sys.exit("Could not read {}: {}".format(path, err))


def load_roster(path):
    data = load_json(path)
    return {s["id"]: s["name"] for s in data.get("students", [])}


def pick_authoritative(files):
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
                sys.exit("{}: missing '{}' -- not a v2 export?".format(path, field))
        by_ta[data["ta"]].append((data["exported"], path, data))

    chosen = {}
    warnings = []
    for ta, entries in by_ta.items():
        entries.sort(key=lambda e: e[0], reverse=True)
        newest = entries[0]
        chosen[ta] = {"path": newest[1], "data": newest[2]}
        newest_blocks = {b["block_id"] for b in newest[2]["blocks"]}
        for exported, path, data in entries[1:]:
            missing = {b["block_id"] for b in data["blocks"]} - newest_blocks
            if missing:
                warnings.append(
                    "{}: {} has block(s) {} not present in the newer export {} "
                    "for the same TA -- possible data loss, check by hand."
                    .format(ta, path, sorted(missing), newest[1])
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


def merge(chosen, roster):
    """Combine the authoritative per-TA data into one record per block_id."""
    by_block = defaultdict(lambda: {"week": None, "half": None,
                                     "conditions": {}, "groups": defaultdict(list)})

    for ta, entry in chosen.items():
        for b in entry["data"]["blocks"]:
            rec = by_block[b["block_id"]]
            rec["week"] = b["week"]
            rec["half"] = b["half"]
            rec["conditions"][ta] = b["condition"]
            for g in b["groups"]:
                rec["groups"][g["group"]].append({
                    "ta": ta,
                    "students": g["students"],
                    "no_part": g.get("no_part", []),
                    "scores": g.get("scores", {}),
                    "progress": g.get("progress"),
                    "counts": g.get("counts", {}),
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

        for gnum in sorted(rec["groups"]):
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
            "condition": condition, "raters": sorted(rec["conditions"]),
            "groups": groups_out,
            "present": sorted(present), "not_seen": not_seen,
            "issues": issues,
        })
        global_issues.extend("{}: {}".format(block_id, i) for i in issues)

    return blocks_out, agreement_out, global_issues


def write_outputs(blocks, agreement, issues, chosen, roster, warnings, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)

    with open(out_dir / "blocks.json", "w", encoding="utf-8") as fh:
        json.dump({
            "source_files": {ta: str(e["path"]) for ta, e in chosen.items()},
            "roster_size": len(roster),
            "load_warnings": warnings,
            "blocks": blocks,
            "agreement": agreement,
            "issues": issues,
        }, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    with open(out_dir / "groups.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["week", "half", "condition", "group", "ta",
                    "engagement", "collaboration", "progress", "stop_thinking",
                    "n_students", "n_flagged_no_part"])
        for b in blocks:
            for g in b["groups"]:
                for r in g["ratings"]:
                    w.writerow([
                        b["week"], b["half"], b["condition"], g["group"], r["ta"],
                        r["scores"].get("engagement", ""),
                        r["scores"].get("collaboration", ""),
                        r["progress"] or "",
                        r["counts"].get("stopThinking", ""),
                        len(r["students"]), len(r["no_part"]),
                    ])

    with open(out_dir / "membership.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["week", "half", "condition", "group", "ta",
                    "student_id", "student_name", "no_part"])
        for b in blocks:
            for g in b["groups"]:
                for r in g["ratings"]:
                    for sid in r["students"]:
                        w.writerow([
                            b["week"], b["half"], b["condition"], g["group"], r["ta"],
                            sid, roster.get(sid, ""), sid in r["no_part"],
                        ])


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exports", nargs="*",
                    help="export JSON files, one per TA (default: everything "
                         "currently in the shared OneDrive Uploads folder)")
    ap.add_argument("--roster", default=str(DEFAULT_ROSTER), help="path to roster.json")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="output directory")
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
    chosen, load_warnings = pick_authoritative(paths)
    blocks, agreement, issues = merge(chosen, roster)
    write_outputs(blocks, agreement, issues, chosen, roster, load_warnings, Path(args.out))

    print("Merged {} TA(s) across {} block(s) -> {}".format(len(chosen), len(blocks), args.out))
    for ta, entry in sorted(chosen.items()):
        print("  {} <- {}".format(ta, entry["path"]))

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
