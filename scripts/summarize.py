#!/usr/bin/env python3
"""Summary statistics over data/merged/groups.csv and membership.csv.

Standard library only, matching the rest of scripts/. Reads the output of
merge_exports.py -- run that first. Prints a plain-text report; nothing is
written to disk, and nothing here is a substitute for the real analysis
(weighted kappa, mixed models) noted as still-open in merge_exports.py and in
the Research notes -- this is a first look, meant to be run after each week's
merge to catch problems (a block with no ratings, an empty scale value)
before they compound.

Usage
-----
    python3 scripts/summarize.py                  # data/merged/groups.csv
    python3 scripts/summarize.py path/to/groups.csv
"""
from __future__ import annotations

import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

RATING_KEYS = ["engagement", "collaboration", "stop_thinking"]
SCALE_ORDER = ["Below", "Expected", "Above"]
PROGRESS_ORDER = ["None", "Partial", "Complete"]


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


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/merged/groups.csv")
    if not path.exists():
        sys.exit(f"summarize: no such file: {path} -- run merge_exports.py first")
    rows = load_rows(path)
    if not rows:
        sys.exit(f"summarize: {path} has no rows")

    print(f"HOFI summary -- {path}")
    print(f"{len(rows)} group-block records\n")

    # ---- coverage: which blocks exist, how many groups rated in each -----
    by_block: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        by_block[block_key(r)].append(r)

    print("Blocks")
    for key in sorted(by_block):
        week, half, cond, cg = key
        blk = by_block[key]
        n_groups = len(blk)
        n_students = sum(int(r["n_students"] or 0) for r in blk)
        n_flagged = sum(int(r["n_flagged_no_part"] or 0) for r in blk)
        n_rated = sum(1 for r in blk if any(r.get(k) for k in RATING_KEYS))
        label = f"w{week}-{half}" + (f"-G{cg}" if cg != "-" else "")
        print(f"  {label:12s} {cond:3s}  {n_groups:3d} groups  {n_students:3d} students"
              f"  {n_rated}/{n_groups} rated  {n_flagged} flagged")
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
    for a, b in [("engagement", "collaboration"), ("engagement", "stop_thinking"),
                 ("collaboration", "stop_thinking")]:
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
            flags.append(f"  block {key} has {len(blk)} groups with no ratings at all"
                          f" -- expected if this is a G1/G2 membership-only block")
    if not flags:
        print("  none")
    else:
        print("\n".join(flags))


if __name__ == "__main__":
    main()
