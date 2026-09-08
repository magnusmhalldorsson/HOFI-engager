#!/usr/bin/env python3
"""Pull the HOFI student roster from Canvas.

Standard library only -- no pip install, works on the system Python 3.9 that
ships with macOS.

The Canvas token is never written into the roster file and never leaves this
machine: the phones only ever see the roster, not the credential.

It is looked for in three places, in order:

    1. the CANVAS_TOKEN environment variable      (handy for a one-off)
    2. the macOS Keychain, service "hofi-canvas"  (the permanent setup)
    3. canvas_token in config.json                (gitignored fallback)

For the permanent setup, store it in the Keychain once -- you type the token at
the prompt, it goes straight into the Keychain, and it is never on disk in the
clear. Note the -U: without it, a second run adds a DUPLICATE entry rather than
replacing the old one, and the stale copy may be the one that gets read back.

    security add-generic-password -a "$USER" -s hofi-canvas -U -w

Check it worked -- this reports the source and length and asks Canvas who you
are, without ever printing the token:

    python3 scripts/fetch_roster.py check

Create the token at Canvas > Account > Settings > New Access Token, and leave
the expiry field blank so it does not need renewing. Some institutions cap
token lifetime centrally; if RU does, the 401 handler below will say so when
the day comes.

Usage
-----
    python3 scripts/fetch_roster.py courses          # find your course id
    python3 scripts/fetch_roster.py roster           # write data/roster.json

canvas_course_id accepts either the numeric Canvas id or RU's SIS id, e.g.
"DCS-T-101-HOFI:41057:20263". Resolving an SIS id needs the right permission on
your Canvas account; if it 404s, use the numeric id.

Every enrolled student ends up in the roster, including anyone taught
elsewhere (e.g. Akureyri). That is deliberate: the app only ever records a
student when a TA taps them in, so someone who never attends a Reykjavik
session simply never appears in any block's data. There is nothing to
pre-filter, and so nothing here that can go stale.

Only the fields the app actually needs are requested. Canvas will happily hand
over e-mail addresses and login ids; we do not ask for them, because the app
has no use for them and unneeded personal data is a liability.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
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


KEYCHAIN_SERVICE = "hofi-canvas"


def course_ref(cfg):
    """The path segment identifying the course.

    canvas_course_id may be either the numeric Canvas id (from the course URL)
    or the SIS id RU's student system pushes in, e.g.

        DCS-T-101-HOFI:41057:20263

    Canvas accepts an SIS id anywhere a course id goes, written as
    'sis_course_id:<id>'. The colons inside the SIS id have to be percent-encoded
    or Canvas reads them as part of the prefix syntax and 404s.
    """
    raw = cfg.get("canvas_course_id")
    if raw is None or str(raw).strip() == "":
        sys.exit("Set canvas_course_id in config.json (run the 'courses' command to find it).")
    raw = str(raw).strip()
    if raw.isdigit():
        return raw
    return "sis_course_id:" + urllib.parse.quote(raw, safe="")


def keychain_token():
    """Read the token from the macOS Keychain, or None if it is not there.

    Shelling out to /usr/bin/security keeps this stdlib-only and means the
    secret is never stored in a file we manage.
    """
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    tok = out.stdout.strip()
    return tok or None


def token(cfg):
    tok = os.environ.get("CANVAS_TOKEN") or keychain_token() or cfg.get("canvas_token")
    if not tok:
        sys.exit(
            "No Canvas token found.\n"
            "\n"
            "Store one in the Keychain (recommended -- do this once):\n"
            '    security add-generic-password -a "$USER" -s {} -w\n'
            "\n"
            "Or for a one-off:  export CANVAS_TOKEN='...'\n"
            "\n"
            "Create the token at: Canvas > Account > Settings > New Access Token\n"
            "Leave the expiry blank so it does not need renewing.".format(KEYCHAIN_SERVICE)
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
                sys.exit(
                    "Canvas rejected the token (401).\n"
                    "\n"
                    "Diagnose first -- this says which copy is being used and how long\n"
                    "it is, without printing it:\n"
                    "    python3 scripts/fetch_roster.py check\n"
                    "\n"
                    "To replace it, delete EVERY stored copy first; a leftover duplicate\n"
                    "under the same service name can shadow the new one:\n"
                    '    while security delete-generic-password -s {} >/dev/null 2>&1; do :; done\n'
                    '    security add-generic-password -a "$USER" -s {} -U -w'
                    .format(KEYCHAIN_SERVICE, KEYCHAIN_SERVICE)
                )
            if err.code == 404:
                sys.exit(
                    "Not found (404).\n"
                    "Check canvas_course_id and canvas_host. If you used the SIS id\n"
                    "(the DCS-T-...:...:... form), your Canvas account may not have\n"
                    "permission to resolve SIS ids -- run  fetch_roster.py courses\n"
                    "and use the numeric id from the first column instead."
                )
            sys.exit("Canvas returned {} for {}".format(err.code, url))
        except urllib.error.URLError as err:
            sys.exit("Could not reach {}: {}".format(host, err.reason))

        for item in payload:
            yield item

        match = re.search(r'<([^>]+)>;\s*rel="next"', link)
        url = match.group(1) if match else None


def get_one(host, path, tok):
    """GET a single JSON object (not a paginated list). Returns (ok, payload_or_msg)."""
    url = "https://{}/api/v1{}".format(host, path)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return True, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return False, "HTTP {}".format(err.code)
    except urllib.error.URLError as err:
        return False, "unreachable: {}".format(err.reason)


def cmd_check(cfg, tok):
    """Say where the token came from and whether Canvas accepts it.

    Never prints the token: length and a short hash are enough to tell two
    tokens apart, and a Canvas token is long enough that the length alone
    catches the usual mistake of storing the wrong thing.
    """
    if os.environ.get("CANVAS_TOKEN"):
        source = "CANVAS_TOKEN environment variable"
    elif keychain_token():
        source = 'macOS Keychain (service "{}")'.format(KEYCHAIN_SERVICE)
    else:
        source = "canvas_token in config.json"

    print("token source : {}".format(source))
    print("token length : {} characters".format(len(tok)))
    print("fingerprint  : {}".format(hashlib.sha256(tok.encode()).hexdigest()[:8]))
    if len(tok) < 40:
        print("  ^ suspiciously short. Canvas tokens are typically 60-80 characters,")
        print("    usually shaped like  1234~AbCdEf...  If this is much shorter, the")
        print("    stored value is probably not the token.")

    print("host         : {}".format(cfg.get("canvas_host")))
    ok, res = get_one(cfg["canvas_host"], "/users/self", tok)
    if not ok:
        print("auth         : FAILED ({})".format(res))
        if res == "HTTP 401":
            print()
            print("Replace the stored token. Delete every copy first -- a second entry")
            print("with the same service name will shadow the new one:")
            print('    while security delete-generic-password -s {} >/dev/null 2>&1; do :; done'
                  .format(KEYCHAIN_SERVICE))
            print('    security add-generic-password -a "$USER" -s {} -U -w'
                  .format(KEYCHAIN_SERVICE))
        return
    print("auth         : ok")
    print("logged in as : {} (id {})".format(res.get("name", "?"), res.get("id", "?")))

    ref = cfg.get("canvas_course_id")
    if ref:
        ok, res = get_one(cfg["canvas_host"], "/courses/{}".format(course_ref(cfg)), tok)
        if ok:
            print("course       : {} (id {})".format(res.get("name", "?"), res.get("id", "?")))
        else:
            print("course       : FAILED ({}) for canvas_course_id={!r}".format(res, ref))


def cmd_courses(cfg, tok):
    """List courses you teach, so you can find the course id."""
    rows = list(get_pages(cfg["canvas_host"], "/courses", tok,
                          {"enrollment_type": "teacher", "per_page": 100}))
    if not rows:
        print("No courses found where you are enrolled as a teacher.")
        return
    print("{:>10}  {:<34}  {}".format("ID", "SIS ID", "COURSE"))
    for course in rows:
        print("{:>10}  {:<34}  {}".format(
            course.get("id"),
            course.get("sis_course_id") or "-",
            course.get("name", "?")))
    print("\nPut either column into config.json as canvas_course_id -- the numeric")
    print("id or the SIS id; the script accepts both.")


def cmd_roster(cfg, tok):
    ref = course_ref(cfg)

    users = list(get_pages(
        cfg["canvas_host"],
        "/courses/{}/users".format(ref),
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
        "canvas_course_id": cfg.get("canvas_course_id"),
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
    parser.add_argument("command", choices=["check", "courses", "roster"],
                        help="'check' tests the token; 'courses' lists your course ids; "
                             "'roster' writes data/roster.json")
    args = parser.parse_args()

    cfg = load_config()
    tok = token(cfg)

    if args.command == "check":
        cmd_check(cfg, tok)
    elif args.command == "courses":
        cmd_courses(cfg, tok)
    else:
        cmd_roster(cfg, tok)


if __name__ == "__main__":
    main()
