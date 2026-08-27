#!/usr/bin/env python3
"""File TA exports that arrived by hand into one local, self-describing inbox.

Standard library only, matching the rest of scripts/.

Why this exists
---------------
In practice the TAs hand their exports over by mail or AirDrop as often as they
upload them to OneDrive, so the files land in Downloads with names the operating
system chose:

    hofi-w01-02-valur (1).json   hofi-w01-02-valur (2).json
    hofi-w01-02-valur (3).json   hofi-w01-02-valur (4).json

Three problems with that, all of which have already bitten:

  1. "(3)" and "(4)" say nothing about which is newer or which has more in it.
     In week 1 the file with the "(1)" suffix turned out to be the FULLER one.
  2. "w01-02" is the app's own tag for an export spanning weeks 1 to 2. It is
     accurate and useless for finding week 2.
  3. Re-exports pile up. `(4)` was a byte-for-byte re-export of `(3)` a day
     later -- identical blocks, different timestamp -- and nothing said so.

So this renames each file after what is actually inside it, refuses to file the
same content twice, and keeps an index you can read.

    scripts/collect_exports.py ~/Downloads/*.json     # file whatever arrived
    scripts/collect_exports.py <folder>               # or a whole folder
    scripts/collect_exports.py --list                 # just show the inbox
    scripts/collect_exports.py ... --move             # move instead of copy

Filed as `data/exports/<exported-timestamp>-<ta>.json`, which sorts
chronologically and never collides. `data/` is gitignored, so nothing here
reaches version control.

Then merge straight from it:

    python3 scripts/merge_exports.py data/exports/*.json --union
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "data" / "exports"
INDEX = INBOX / "INDEX.md"


def slug(s: str) -> str:
    s = (s or "unknown").lower()
    for a, b in (("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ý","y"),
                 ("þ","th"),("æ","ae"),("ö","o"),("ð","d")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "", s) or "unknown"


def content_key(data: dict) -> str:
    """Hash of what was RECORDED, deliberately ignoring `exported`.

    Two exports of an unchanged phone differ only in their timestamp. Hashing
    the blocks alone is what lets this say "you already have this" instead of
    filing a fifth copy.
    """
    return hashlib.sha256(
        json.dumps(data.get("blocks", []), sort_keys=True, ensure_ascii=False)
        .encode("utf-8")).hexdigest()


def describe(data: dict) -> list[dict]:
    out = []
    for b in data.get("blocks", []):
        groups = b.get("groups", [])
        out.append({
            "id": b.get("block_id", "?"),
            "week": b.get("week"), "half": b.get("half"),
            "cohort": b.get("cohort_group"),
            "groups": len(groups),
            "students": len({s for g in groups for s in g.get("students", [])}),
        })
    return out


def read_export(p: Path):
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return None, f"not readable JSON ({e.__class__.__name__})"
    for f in ("ta", "exported", "blocks"):
        if f not in data:
            return None, f"missing '{f}' — not a HOFI export?"
    return data, None


def filed() -> dict[str, Path]:
    """content-key -> path, for everything already in the inbox."""
    seen = {}
    for p in sorted(INBOX.glob("*.json")):
        data, err = read_export(p)
        if data:
            seen[content_key(data)] = p
    return seen


def write_index() -> None:
    rows = []
    for p in sorted(INBOX.glob("*.json")):
        data, err = read_export(p)
        if not data:
            continue
        rows.append((p, data, describe(data)))
    lines = ["# TA exports — local inbox", "",
             f"{len(rows)} file(s). Filed by `scripts/collect_exports.py`; "
             "named after the export timestamp inside each file, so they sort "
             "chronologically and never collide.", "",
             "Merge everything here with:", "",
             "```bash",
             "python3 scripts/merge_exports.py data/exports/*.json --union",
             "```", "",
             "| File | TA | Exported | Blocks | Covers |",
             "|---|---|---|---|---|"]
    for p, data, blocks in rows:
        covers = ", ".join(sorted({f"wk{b['week']} {b['half']}" for b in blocks})) or "—"
        lines.append(f"| `{p.name}` | {data['ta']} | {data['exported'][:19].replace('T',' ')} "
                     f"| {len(blocks)} | {covers} |")
    lines += ["", "## What is in each", ""]
    for p, data, blocks in rows:
        lines.append(f"**`{p.name}`** — {data['ta']}")
        for b in blocks:
            c = f" cohort {b['cohort']}" if b["cohort"] else ""
            lines.append(f"- `{b['id']}` wk{b['week']} {b['half']}{c} — "
                         f"{b['groups']} groups, {b['students']} students")
        lines.append("")
    INDEX.write_text("\n".join(lines) + "\n", encoding="utf-8")


def show_inbox() -> None:
    rows = [(p, *read_export(p)) for p in sorted(INBOX.glob("*.json"))]
    rows = [(p, d) for p, d, e in rows if d]
    if not rows:
        print(f"Inbox is empty: {INBOX}")
        return
    print(f"{INBOX}  —  {len(rows)} file(s)\n")
    by_ta = defaultdict(list)
    for p, d in rows:
        by_ta[d["ta"]].append((p, d))
    for ta in sorted(by_ta):
        print(f"  {ta}")
        for p, d in sorted(by_ta[ta], key=lambda x: x[1]["exported"]):
            blocks = describe(d)
            covers = ", ".join(sorted({f"wk{b['week']} {b['half']}" for b in blocks}))
            tot = sum(b["students"] for b in blocks)
            print(f"    {p.name:<34} {d['exported'][:16].replace('T',' ')}  "
                  f"{len(blocks)} blocks, {tot} seats   {covers}")
    print(f"\n  merge:  python3 scripts/merge_exports.py data/exports/*.json --union")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="*", type=Path,
                    help="files, or folders to scan for *.json")
    ap.add_argument("--move", action="store_true", help="move rather than copy")
    ap.add_argument("--list", action="store_true", help="show the inbox and stop")
    a = ap.parse_args()

    INBOX.mkdir(parents=True, exist_ok=True)
    if a.list or not a.paths:
        show_inbox()
        return

    incoming: list[Path] = []
    for p in a.paths:
        if p.is_dir():
            incoming += sorted(p.glob("*.json"))
        elif p.is_file():
            incoming.append(p)
        else:
            print(f"  ? no such path: {p}", file=sys.stderr)

    known = filed()
    added = dupes = bad = 0
    for src in incoming:
        if src.resolve().parent == INBOX.resolve():
            continue                                     # already filed
        data, err = read_export(src)
        if err:
            print(f"  SKIP  {src.name}: {err}"); bad += 1; continue
        key = content_key(data)
        if key in known:
            print(f"  dup   {src.name}\n           same content as {known[key].name} "
                  f"— exported again, nothing new recorded")
            dupes += 1
            continue
        stamp = re.sub(r"[^0-9]", "", data["exported"][:19])   # YYYYMMDDHHMMSS
        name = f"{stamp[:8]}T{stamp[8:14]}-{slug(data['ta'])}.json"
        dst = INBOX / name
        n = 2
        while dst.exists():
            dst = INBOX / f"{name[:-5]}-{n}.json"; n += 1
        (shutil.move if a.move else shutil.copy2)(str(src), str(dst))
        blocks = describe(data)
        covers = ", ".join(sorted({f"wk{b['week']} {b['half']}" for b in blocks}))
        print(f"  filed {dst.name}   {data['ta']}, {len(blocks)} blocks   {covers}")
        known[key] = dst
        added += 1

    write_index()
    print(f"\n{added} filed, {dupes} duplicate(s) skipped"
          + (f", {bad} unreadable" if bad else "") + f"  →  {INBOX}")
    print(f"index: {INDEX.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
