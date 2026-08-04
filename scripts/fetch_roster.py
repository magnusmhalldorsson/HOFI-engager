#!/usr/bin/env python3
"""Pull the HOFI student roster from Canvas.

Standard library only -- no pip install, works on the system Python 3.9 that
ships with macOS.

The Canvas token stays in your environment or in config.json, which is
gitignored. It is never written into the roster file and never leaves this
machine: the phones only ever see the roster, not the credential.

Usage
-----
    export CANVAS_TOKEN='...'          # from Canvas > Account > Settings
    python3 scripts/fetch_roster.py courses          # find your course id
    python3 scripts/fetch_roster.py roster           # write data/roster.json

Only the fields the app actually needs are requested. Canvas will happily hand
over e-mail addresses and login ids; we do not ask for them, because the app
has no use for them and unneeded personal data is a liability.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
ROSTER_PATH = ROOT / "data" / "roster.json"


def load_config():
    if not CONFIG_PATH.exists():
        sys.exit(
            "No config.json found.\n"
            "Copy config.example.json to config.json and fill in your Canvas host."
        )
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def token(cfg):
    tok = os.environ.get("CANVAS_TOKEN") or cfg.get("canvas_token")
    if not tok:
        sys.exit(
            "No Canvas token.\n"
            "Either  export CANVAS_TOKEN='...'  or set canvas_token in config.json.\n"
            "Create one at:  Canvas > Account > Settings > New Access Token"
        )
    return tok


def get_pages(host, path, tok, params=None):
    """Yield items from a paginated Canvas endpoint, following Link headers."""
    url = "https://{}/api/v1{}".format(host, path)
    if params:
        pairs = []
        for key, value in params.items():
            if isinstance(value, (list, tuple)):
                pairs += ["{}={}".format(key, v) for v in value]
            else:
                pairs.append("{}={}".format(key, value))
        url += "?" + "&".join(pairs)

    while url:
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                link = resp.headers.get("Link", "")
        except urllib.error.HTTPError as err:
            if err.code == 401:
                sys.exit("Canvas rejected the token (401). Has it expired?")
            if err.code == 404:
                sys.exit("Not found (404): check the course id and the Canvas host.")
            sys.exit("Canvas returned {} for {}".format(err.code, url))
        except urllib.error.URLError as err:
            sys.exit("Could not reach {}: {}".format(host, err.reason))

        for item in payload:
            yield item

        match = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = match.group(1) if match else None


def cmd_courses(cfg, tok):
    """List courses you teach, so you can find the course id."""
    rows = list(get_pages(cfg["canvas_host"], "/courses", tok,
                          {"enrollment_type": "teacher", "per_page": 100}))
    if not rows:
        print("No courses found where you are enrolled as a teacher.")
        return
    print("{:>10}  {}".format("ID", "COURSE"))
    for course in rows:
        print("{:>10}  {}".format(course.get("id"), course.get("name", "?")))
    print("\nPut the id in config.json as canvas_course_id.")


def cmd_roster(cfg, tok):
    course_id = cfg.get("canvas_course_id")
    if not course_id:
        sys.exit("Set canvas_course_id in config.json (run the 'courses' command to find it).")

    users = list(get_pages(
        cfg["canvas_host"],
        "/courses/{}/users".format(course_id),
        tok,
        {"enrollment_type[]": "student", "enrollment_state[]": "active", "per_page": 100},
    ))

    students = []
    for user in users:
        students.append({
            "id": str(user["id"]),
            "name": user.get("name", "").strip(),
            "sortable": user.get("sortable_name", "").strip(),
        })

    # Canvas can return a student more than once across pages when enrollments
    # change mid-fetch; keep the first of each id.
    seen = set()
    unique = []
    for student in students:
        if student["id"] not in seen:
            seen.add(student["id"])
            unique.append(student)
    unique.sort(key=lambda s: s["sortable"] or s["name"])

    roster = {
        "course": cfg.get("course_label", "HOFI"),
        "canvas_course_id": course_id,
        "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "students": unique,
    }

    ROSTER_PATH.parent.mkdir(parents=True, exist_ok=True)

    previous = None
    if ROSTER_PATH.exists():
        try:
            with open(ROSTER_PATH, encoding="utf-8") as fh:
                previous = json.load(fh)
        except (ValueError, OSError):
            previous = None

    with open(ROSTER_PATH, "w", encoding="utf-8") as fh:
        json.dump(roster, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print("Wrote {} ({} students).".format(ROSTER_PATH, len(unique)))

    if previous:
        before = {s["id"] for s in previous.get("students", [])}
        after = {s["id"] for s in unique}
        names = {s["id"]: s["name"] for s in unique}
        old_names = {s["id"]: s["name"] for s in previous.get("students", [])}
        added = after - before
        dropped = before - after
        for sid in sorted(added):
            print("  + {}".format(names.get(sid, sid)))
        for sid in sorted(dropped):
            print("  - {}".format(old_names.get(sid, sid)))
        if not added and not dropped:
            print("  no change since last fetch")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["courses", "roster"],
                        help="'courses' lists your course ids; 'roster' writes data/roster.json")
    args = parser.parse_args()

    cfg = load_config()
    tok = token(cfg)

    if args.command == "courses":
        cmd_courses(cfg, tok)
    else:
        cmd_roster(cfg, tok)


if __name__ == "__main__":
    main()
