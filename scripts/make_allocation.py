#!/usr/bin/env python3
"""Draw the sealed AM/PM order allocation for weeks 2-12 and write app/allocation.json.

The study has exactly one randomisation: which cohort group takes the Thinking Lab
first, flipped between morning and afternoon, decided per teaching day. The design and
the pre-registration both promise "with the seed recorded in advance" -- which is a
promise a reviewer can check, and one that quietly fails if it means remembering to flip
a coin on eleven separate Wednesday mornings.

So the whole sequence is drawn once, now, from a seed recorded in the pre-registration.
Anyone holding the seed can regenerate the file and confirm it was not adjusted later.
That is the entire point; the randomness matters less than the auditability.

One bit per teaching day: it decides the morning, and the afternoon is its complement.

    python3 scripts/make_allocation.py --seed <seed>     # regenerate and verify
    python3 scripts/make_allocation.py --new-seed        # draw a fresh seed (once only)

NOT a TC/OC allocation. Earlier drafts of TODO.md called for one; that predates the
2026-08-19 correction. There is nothing to allocate between TC and OC: every half-day runs
a Thinking Lab (TC) and then an Open Challenge (OC), always in that order. Both half-days
have the same structure. "OC" means Open Challenge throughout -- there is no ordinary
class in this course.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "allocation.json"

WEEK1 = datetime.date(2026, 8, 19)   # HOFI week 1, taught before consent, outside the study
FIRST, LAST = 2, 12                  # the observed weeks
FINAL_PROJECT = {11, 12}


def week_date(week: int) -> datetime.date:
    return WEEK1 + datetime.timedelta(days=7 * (week - 1))


def bit(seed: str, week: int) -> int:
    """Low bit of SHA-256(seed|week). Deterministic, and checkable by hand."""
    h = hashlib.sha256(("%s|week%d" % (seed, week)).encode("utf-8")).hexdigest()
    return int(h[-1], 16) & 1


def build(seed: str) -> dict:
    weeks = []
    for w in range(FIRST, LAST + 1):
        am_first = "2" if bit(seed, w) else "1"
        pm_first = "1" if am_first == "2" else "2"
        entry = {
            "week": w,
            "date": week_date(w).isoformat(),
            "AM": {"thinking_lab_first": am_first,
                   "thinking_lab_second": pm_first},
            "PM": {"thinking_lab_first": pm_first,
                   "thinking_lab_second": am_first},
        }
        if w in FINAL_PROJECT:
            entry["note"] = ("final-project week -- included for completeness; the Thinking "
                             "Lab may not run in this form")
        weeks.append(entry)
    return {
        "course": "HOFI",
        "drawn": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "seed": seed,
        "method": ("low bit of SHA-256('<seed>|week<n>'): 0 -> Group 1 takes the Thinking "
                   "Lab first in the morning, 1 -> Group 2 does. The afternoon is the "
                   "complement of the morning."),
        "covers": "weeks %d-%d; week 1 (%s) is outside the study" % (
            FIRST, LAST, WEEK1.isoformat()),
        "weeks": weeks,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", help="the recorded seed; regenerates the identical file")
    ap.add_argument("--new-seed", action="store_true",
                    help="draw a fresh seed -- do this once, then record it")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--check", action="store_true",
                    help="regenerate from --seed and compare with the file on disk")
    a = ap.parse_args()

    if a.new_seed and a.seed:
        ap.error("--new-seed and --seed are mutually exclusive")
    if a.new_seed:
        seed = secrets.token_hex(8)
    elif a.seed:
        seed = a.seed
    elif a.out.exists():
        seed = json.loads(a.out.read_text(encoding="utf-8"))["seed"]
    else:
        ap.error("no seed: pass --seed, or --new-seed to draw one")

    data = build(seed)

    if a.check:
        on_disk = json.loads(a.out.read_text(encoding="utf-8"))
        same = on_disk["weeks"] == data["weeks"] and on_disk["seed"] == seed
        print("MATCHES the sealed file" if same else "DIFFERS from the sealed file")
        raise SystemExit(0 if same else 1)

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    print("seed: %s" % seed)
    print("  record this in the pre-registration -- it is what makes the draw auditable\n")
    print("written: %s\n" % a.out)
    print("  week  date        AM: TL first   PM: TL first")
    for w in data["weeks"]:
        print("   %2d   %s     Group %s        Group %s%s" % (
            w["week"], w["date"], w["AM"]["thinking_lab_first"],
            w["PM"]["thinking_lab_first"], "   (final project)" if "note" in w else ""))


if __name__ == "__main__":
    main()
