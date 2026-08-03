#!/usr/bin/env python3
"""new_brief.py — file a task for a post, usually a trending peg.

`briefs/` is the task inbox. One file per task. A brief is not a draft and never
becomes one automatically: it records what somebody wants written and, more
importantly, forces the standing-gate answer to be written down before a drafter
picks it up.

The standing-gate law: before riding any news peg, name a credible, non
manufactured reason this account can speak on it. "It is about AI and we do AI"
is manufactured relevance. If the reason field is empty, the drafter refuses the
brief. That refusal is the point of this file existing.

Usage:
    python3 scripts/new_brief.py "OpenAI ships agent memory" \\
        --url https://example.com/story --icp msp \\
        --reason "we sell the own-cloud version of exactly this"
    python3 scripts/new_brief.py --list
    python3 scripts/new_brief.py --list --open
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BRIEFS = REPO / "briefs"
ICPS = ("msp", "fund-family-office", "healthcare", "smb", "other")

TEMPLATE = """<!--
status: open
peg: {peg}
source: {url}
icp: {icp}
objective: {objective}
filed: {today}
-->
# {peg}

## Standing gate

Why can this account speak on this, credibly, without manufacturing the link?

{reason}

**If that answer is empty or reads as "it is about AI and we do AI", the drafter must
refuse this brief.** Manufactured relevance is the most common way a news post turns
into a post nobody engages with, and the law is in `doctrine/PATTERNS.md`.

## What the drafter must still choose

- One pain from `pain/PAIN-MATRIX.md`, in the ICP's own words. Not a pain invented
  to fit the peg.
- One shape from `doctrine/BODY-PATTERNS.md`, and not the shape used by the last
  post that shipped.
- One CTA keyword, unused in the last 14 days.

## Claim budget

Anything this peg tempts you to say that is not already in
`doctrine/VERIFIED-CLAIMS.md` needs a source and a check date added there first,
by a human. List those here as you find them:

- [ ] (none yet)

## Outcome

Fill this in when the brief is worked, so the inbox does not silently grow:

- draft:
- score:
- refused, and why:
"""


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return "-".join(s.split("-")[:6]) or "brief"


def list_briefs(only_open: bool) -> int:
    if not BRIEFS.exists():
        print("no briefs/ directory yet")
        return 0
    files = sorted(BRIEFS.glob("*.md"))
    files = [f for f in files if f.name != "README.md"]
    if not files:
        print("inbox empty")
        return 0
    for f in files:
        head = f.read_text(encoding="utf-8")[:400]
        status = re.search(r"^status:\s*(\S+)", head, re.M)
        status = status.group(1) if status else "?"
        if only_open and status != "open":
            continue
        icp = re.search(r"^icp:\s*(\S+)", head, re.M)
        print(f"{status:8} {icp.group(1) if icp else '?':20} {f.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("peg", nargs="?", help="the trending thing, in a few words")
    ap.add_argument("--url", default="", help="source link for the peg")
    ap.add_argument("--icp", default="smb", choices=ICPS)
    ap.add_argument("--objective", default="pilot signups", help="what this post is for")
    ap.add_argument("--reason", default="", help="the standing-gate answer")
    ap.add_argument("--list", action="store_true", help="list the inbox")
    ap.add_argument("--open", action="store_true", help="with --list, show open briefs only")
    args = ap.parse_args()

    if args.list:
        return list_briefs(args.open)
    if not args.peg:
        ap.error("give a peg, or pass --list")

    BRIEFS.mkdir(exist_ok=True)
    path = BRIEFS / f"{date.today().isoformat()}-{slugify(args.peg)}.md"
    if path.exists():
        sys.exit(f"{path} already exists")

    reason = args.reason.strip() or "**UNANSWERED. The drafter must refuse this brief until a human fills this in.**"
    path.write_text(TEMPLATE.format(
        peg=args.peg, url=args.url or "none given", icp=args.icp,
        objective=args.objective, today=date.today().isoformat(), reason=reason,
    ), encoding="utf-8")

    print(f"filed {path}")
    if not args.reason.strip():
        print("  standing gate UNANSWERED. This brief is not draftable yet, by law.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
