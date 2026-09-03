#!/usr/bin/env python3
"""Summary statistics over data/merged/groups.csv and membership.csv.

Standard library only, matching the rest of scripts/. Reads the output of
merge_exports.py -- run that first. Prints a plain-text report; nothing is
written to disk, and nothing here is a substitute for the real analysis
(weighted kappa, mixed models) noted as still-open in merge_exports.py and in
the Research notes -- this is a first look, meant to be run after each week's
merge to catch problems (a block with no ratings, an empty scale value)
before they compound.

Counting: a group is a group, not a row
---------------------------------------
groups.csv holds one row per (group x TA), so on a calibration day -- both TAs
deliberately rating the same groups -- every group and every student appears
twice. Summing those rows produced a week-3 report claiming 119 students in a
PM session on a 94-student roster. Group and student counts here are therefore
DISTINCT counts; the row count is reported separately as "ratings", because
that is the meaningful denominator for the agreement figures further down.

Distinct students need membership.csv, which is read from alongside groups.csv.
Without it the count falls back to the largest headcount any one TA logged for
each group, which is close but not exact, and the report says so.

Cohort groups do not add up
---------------------------
G1 and G2 are the two complementary halves of one Thinking-Lab population, so
adding their two headcounts does not give a half-day total. The half-day
section below reports the distinct union, which is the number to quote as
"how many were in the room".

Flags come from blocks.json
---------------------------
merge_exports.py records real data-quality problems (two TAs logging different
progress for the same group, a student in two groups) in blocks.json, not in
groups.csv. Reading only the CSV meant this report said "Flags: none" while 29
unresolved issues sat in the merge output. blocks.json is now read from
alongside groups.csv and its issues are printed here.

Usage
-----
    python3 scripts/summarize.py                  # data/merged/groups.csv
    python3 scripts/summarize.py path/to/groups.csv
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

RATING_KEYS = ["engagement", "collaboration", "self_reliance"]
SCALE_ORDER = ["Below", "Expected", "Above"]
PROGRESS_ORDER = ["None", "Partial", "Complete"]

MAX_ISSUES_SHOWN = 12


def load_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rating_dist(rows: list[dict], key: str) -> Counter:
    return Counter(r[key] for r in rows if r.get(key))


def fmt_dist(dist: Counter, order: list[str]) -> str:
    total = sum(dist.values())
    if not total:
        return "no ratings"
    parts = []
    for label in order:
        n = dist.get(label, 0)
        parts.append(f"{label} {n} ({n/total:.0%})")
    extra = set(dist) - set(order)
    for label in sorted(extra):
        parts.append(f"{label} {dist[label]}")
    return ", ".join(parts) + f"  [n={total}]"


def block_key(r: dict) -> tuple:
    return (r["week"], r["half"], r["condition"], r["cohort_group"] or "-")


def block_label(key: tuple) -> str:
    week, half, _cond, cg = key
    return f"w{week}-{half}" + (f"-G{cg}" if cg != "-" else "")


def load_membership(path: Path) -> tuple[dict, dict, dict] | None:
    """Distinct students per block, per half-day, and distinct no-part flags.

    Returns None if membership.csv is not next to groups.csv, in which case the
    caller falls back to the per-group maximum headcount.
    """
    if not path.exists():
        return None
    by_block: dict[tuple, set] = defaultdict(set)
    by_half: dict[tuple, set] = defaultdict(set)
    flagged: dict[tuple, set] = defaultdict(set)
    for r in load_rows(path):
        key = block_key(r)
        by_block[key].add(r["student_id"])
        by_half[(r["week"], r["half"])].add(r["student_id"])
        if r.get("no_part", "").strip().lower() == "true":
            flagged[key].add(r["student_id"])
    return by_block, by_half, flagged


def load_issues(path: Path) -> list[str] | None:
    """merge_exports.py's own data-quality findings. None if blocks.json is absent."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return list(data.get("issues", []))


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/merged/groups.csv")
    if not path.exists():
        sys.exit(f"summarize: no such file: {path} -- run merge_exports.py first")
    rows = load_rows(path)
    if not rows:
        sys.exit(f"summarize: {path} has no rows")

    membership = load_membership(path.with_name("membership.csv"))
    blocks_path = path.with_name("blocks.json")
    issues = load_issues(blocks_path)

    by_block: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        by_block[block_key(r)].append(r)

    print(f"HOFI summary -- {path}")
    print(f"{len(rows)} ratings of {len(by_block)} blocks"
          f" ({sum(len({r['group'] for r in b}) for b in by_block.values())} groups)\n")

    # ---- coverage: which blocks exist, how many groups rated in each -----
    # Counts are DISTINCT groups and DISTINCT students; "ratings" is the row
    # count, which exceeds the group count exactly when two TAs rated the same
    # group -- the calibration overlap, which is intended, not an error.
    print("Blocks")
    for key in sorted(by_block):
        blk = by_block[key]
        groups = {r["group"] for r in blk}
        rated = {r["group"] for r in blk if any(r.get(k) for k in RATING_KEYS)}
        raters = {r["ta"] for r in blk if r["ta"]}
        if membership:
            n_students = len(membership[0].get(key, ()))
            n_flagged = len(membership[2].get(key, ()))
        else:
            # Best available without membership.csv: the largest headcount any one
            # TA logged for each group. Undercounts if two TAs saw different members.
            per_group: dict[str, int] = defaultdict(int)
            flagged_per_group: dict[str, int] = defaultdict(int)
            for r in blk:
                per_group[r["group"]] = max(per_group[r["group"]], int(r["n_students"] or 0))
                flagged_per_group[r["group"]] = max(flagged_per_group[r["group"]],
                                                    int(r["n_flagged_no_part"] or 0))
            n_students = sum(per_group.values())
            n_flagged = sum(flagged_per_group.values())
        rated_col = f"{len(rated)}/{len(groups)} rated"
        print(f"  {block_label(key):12s} {key[2]:3s}  {len(groups):3d} groups"
              f"  {n_students:3d} students  {rated_col:12s}"
              f"  {len(blk):3d} ratings by {len(raters)} TA{'s' if len(raters) != 1 else ''}"
              f"  {n_flagged} flagged")
    if not membership:
        print("\n  ! membership.csv not found next to groups.csv -- student counts are the"
              "\n    per-group maximum across TAs, not a true distinct count.")

    # ---- half-day totals -------------------------------------------------
    # The number to quote as "how many were in the room". G1 + G2 is NOT this:
    # the two cohort groups are complementary halves of one population, and a
    # student recorded in both would be counted twice by adding them.
    if membership:
        print("\nHalf-days (distinct students -- cohort groups are halves, do not add them)")
        by_half = membership[1]
        for hk in sorted(by_half):
            print(f"  w{hk[0]}-{hk[1]}: {len(by_half[hk])} students recorded present")
    print()

    # ---- rating distributions, overall and per condition -----------------
    print("Ratings, all blocks combined")
    for key in RATING_KEYS:
        print(f"  {key:14s} {fmt_dist(rating_dist(rows, key), SCALE_ORDER)}")
    print(f"  {'progress':14s} {fmt_dist(rating_dist(rows, 'progress'), PROGRESS_ORDER)}")
    print()

    conditions = sorted({r["condition"] for r in rows if r["condition"]})
    if len(conditions) > 1:
        print("Ratings by condition")
        for cond in conditions:
            sub = [r for r in rows if r["condition"] == cond]
            print(f"  {cond}:")
            for key in RATING_KEYS:
                print(f"    {key:14s} {fmt_dist(rating_dist(sub, key), SCALE_ORDER)}")

    # ---- inter-construct correlation flag (halo check, see Measurement Plan) --
    def agree_rate(a: str, b: str) -> tuple[int, int] | None:
        pairs = [(r[a], r[b]) for r in rows if r.get(a) and r.get(b)]
        if not pairs:
            return None
        same = sum(1 for x, y in pairs if x == y)
        return same, len(pairs)

    print("\nExact agreement between rated constructs (halo check -- see HOFI Measurement Plan)")
    for a, b in [("engagement", "collaboration"), ("engagement", "self_reliance"),
                 ("collaboration", "self_reliance")]:
        res = agree_rate(a, b)
        if res:
            same, n = res
            print(f"  {a} vs {b}: {same}/{n} exact match ({same/n:.0%})")

    # ---- data-quality flags ------------------------------------------------
    print("\nFlags")
    flags = []
    for key, blk in by_block.items():
        unrated = [r for r in blk if not any(r.get(k) for k in RATING_KEYS)]
        if unrated and len(unrated) == len(blk):
            flags.append(f"  block {block_label(key)} has {len({r['group'] for r in blk})}"
                         f" groups with no ratings at all"
                         f" -- expected if this is a G1/G2 membership-only block")
    if flags:
        print("\n".join(flags))

    if issues is None:
        print("  ! blocks.json not found next to groups.csv -- merge_exports.py's own"
              "\n    findings (progress mismatches, a student in two groups) are NOT"
              "\n    included here. This report cannot see them from the CSV alone.")
    elif issues:
        # merge_exports.py appends the same explanatory clause to every issue of a
        # kind, so 29 issues print as 29 copies of one paragraph. Split each at the
        # first " -- ", list the specifics, and give each distinct rationale once.
        print(f"  {len(issues)} unresolved from merge_exports.py ({blocks_path}):")
        rationales: list[str] = []
        for line in issues[:MAX_ISSUES_SHOWN]:
            head, sep, why = line.partition(" -- ")
            print(f"    - {head}")
            if sep and why not in rationales:
                rationales.append(why)
        if len(issues) > MAX_ISSUES_SHOWN:
            print(f"    ... and {len(issues) - MAX_ISSUES_SHOWN} more; all of them are in"
                  f" {blocks_path.name} under \"issues\".")
        for why in rationales:
            print(f"    ({why})")
    elif not flags:
        print("  none")


if __name__ == "__main__":
    main()
