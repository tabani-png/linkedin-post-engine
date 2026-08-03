#!/usr/bin/env python3
"""
apply_mutation.py — decides whether a proposed skill mutation is legal.

The mutator subagent *proposes*. This script *decides*. That split is deliberate:
upstream's optimiser asks its mutator to "make exactly ONE targeted change" and
then hands it the whole file to rewrite, with nothing verifying the request. A
prompt is not an enforcement mechanism.

Six gates, in order. Any failure is a reject with a reason, and nothing is written.

  1. Immutable pins   — sha256 of the human-owned files must be unchanged.
  2. Frontmatter      — byte-identical.
  3. Anchor block     — present, verbatim. Without this, `restructure` is a legal
                        route to deleting the laws.
  4. One hunk         — a single contiguous change, inside the named section only.
  5. Size caps        — at most 25 added lines, at most 15% total growth.
  6. No new claims    — the claim check runs on the mutated SKILL.md ITSELF, not
                        just on the drafts it produces. This is the defence against
                        the add_example trap: a plausible fake specific baked into
                        the prompt gets reproduced in every future draft forever.

Usage
-----
  python3 scripts/apply_mutation.py --pin                          # write the pin file
  python3 scripts/apply_mutation.py --section "## Shape selection" \
      --candidate runs/2026-07-29-1/r1/candidate-section.md        # dry check
  python3 scripts/apply_mutation.py --section "..." --candidate ... --apply

Exit codes: 0 = legal (and applied, with --apply), 1 = rejected, 2 = bad usage.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / ".claude" / "skills" / "post-drafter" / "SKILL.md"
PINS = REPO / ".sip-pins.json"

# Human-owned. The loop may propose changes to these, never write them.
IMMUTABLE = [
    ".claude/skills/post-drafter/CORE-LAWS.md",
    "doctrine/VERIFIED-CLAIMS.md",
    "doctrine/VOICE-PROFILE-founder.md",
    "pain/PAIN-MATRIX.md",
    "scenarios/scenarios.jsonl",
]

MAX_ADDED_LINES = 25
MAX_GROWTH = 0.15
ANCHOR_START = "<!-- ANCHOR:start"
ANCHOR_END = "<!-- ANCHOR:end -->"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "MISSING"


def write_pins() -> int:
    pins = {rel: sha(REPO / rel) for rel in IMMUTABLE}
    PINS.write_text(json.dumps(pins, indent=2) + "\n", encoding="utf-8")
    print(f"pinned {len(pins)} immutable files -> {PINS.name}")
    for rel, h in pins.items():
        print(f"  {h[:12]}  {rel}")
    return 0


def check_pins() -> list[str]:
    if not PINS.exists():
        return ["no .sip-pins.json — run --pin first (the precheck does this)"]
    pinned = json.loads(PINS.read_text(encoding="utf-8"))
    bad = []
    for rel, expected in pinned.items():
        actual = sha(REPO / rel)
        if actual != expected:
            bad.append(f"{rel}: sha changed ({expected[:12]} -> {actual[:12]})")
    return bad


def split_frontmatter(text: str) -> tuple[str, str]:
    m = re.match(r"(---\n.*?\n---\n)(.*)", text, re.S)
    return (m.group(1), m.group(2)) if m else ("", text)


def find_section(lines: list[str], heading: str) -> tuple[int, int]:
    """Return [start, end) line indices of a '## Heading' section."""
    want = heading.strip()
    level = len(want) - len(want.lstrip("#"))
    start = None
    for i, ln in enumerate(lines):
        if ln.strip() == want:
            start = i
            break
    if start is None:
        return -1, -1
    for j in range(start + 1, len(lines)):
        s = lines[j].lstrip()
        if s.startswith("#"):
            if len(s) - len(s.lstrip("#")) <= level:
                return start, j
    return start, len(lines)


def count_hunks(before: list[str], after: list[str]) -> tuple[int, int, tuple[int, int]]:
    """Return (hunk_count, added_lines, (first_change_lo, first_change_hi)) in `before` coords."""
    sm = difflib.SequenceMatcher(None, before, after, autojunk=False)
    hunks, added, span = 0, 0, None
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        hunks += 1
        added += max(0, (j2 - j1) - (i2 - i1))
        if span is None:
            span = (i1, i2)
        else:
            span = (min(span[0], i1), max(span[1], i2))
    return hunks, added, span or (0, 0)


# A fake specific does not need a dollar sign to be a fabrication. "A 40-tech MSP
# cut onboarding from 3 weeks to 4 days" has no $, no %, no quote marks, and is
# exactly the kind of plausible detail that gets baked into a prompt and then
# reproduced in every future draft as though it were sourced.
OUTCOME_RE = re.compile(
    r"\b(cut|cuts|reduced?|saved?|slashed|dropped|halved|increased?|grew|boosted|"
    r"improved?|shortened)\b[^.\n]{0,60}?\d", re.I)
ENTITY_QTY_RE = re.compile(
    r"\b\d+\s*[-–]?\s*(techs?|persons?|people|employees?|staff|seats?|customers?|"
    r"clients?|compan(?:y|ies)|teams?|MSPs?|users?|firms?|clinics?|funds?)\b", re.I)
FROM_TO_RE = re.compile(
    r"\bfrom\s+\d+\s+\w+\s+to\s+\d+\s+\w+", re.I)


def new_claims(added_text: str) -> list[str]:
    """Any claim in the ADDED lines that the allowlist does not cover.

    Scanning only what the mutation added, rather than the whole file, is what
    makes this usable: the skill legitimately contains instructional numbers
    ("120 to 300 words", "at most 3 named brands", "14 days") that are not claims
    and must not trip the gate.
    """
    sys.path.insert(0, str(REPO / "scripts"))
    import craft_score as cs  # reuse one allowlist parser, never two

    claims = cs.load_claims()
    body = cs.strip_fences(added_text)
    out = []
    for m in OUTCOME_RE.finditer(body):
        out.append(f"outcome claim: {m.group(0).strip()[:60]}")
    for m in ENTITY_QTY_RE.finditer(body):
        out.append(f"entity quantity: {m.group(0).strip()}")
    for m in FROM_TO_RE.finditer(body):
        out.append(f"before/after claim: {m.group(0).strip()}")
    for fig in re.findall(r"\$[\d,.]+\s*[KMB]?", body):
        if cs.normalise_money(fig) not in claims["money"]:
            out.append(f"unsourced figure {fig}")
    for pct in re.findall(r"\b\d{1,3}(?:\.\d+)?\s?%", body):
        out.append(f"unsourced percentage {pct.strip()}")
    for mult in re.findall(r"\b\d+(?:\.\d+)?x\b", body):
        out.append(f"unsourced multiple {mult}")
    for quoted in re.findall(r"[\"“]([^\"”\n]{25,})[\"”]", body):
        out.append(f"quoted span (possible testimonial): {quoted[:50]}...")
    for cert in re.findall(r"\b(SOC ?2|HIPAA|ISO ?270\d\d|BAA|PHI|FINRA|GDPR)\b", body, re.I):
        # A ban that is *named as banned* is fine; an affirmative claim is not.
        for ln in body.splitlines():
            if re.search(rf"\b{re.escape(cert)}\b", ln, re.I) and not re.search(
                r"\b(never|not|no|ban|forbid|blur|imply|must not|may not|fail)\b", ln, re.I
            ):
                out.append(f"certification claim {cert} in: {ln.strip()[:60]}")
                break
    return sorted(set(out))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pin", action="store_true", help="write the immutable pin file")
    ap.add_argument("--section", help="the '## Heading' the mutation targets")
    ap.add_argument("--candidate", type=Path, help="file holding the replacement section")
    ap.add_argument("--apply", action="store_true", help="write SKILL.md in place if legal")
    args = ap.parse_args()

    if args.pin:
        return write_pins()
    if not args.section or not args.candidate:
        ap.error("--section and --candidate are required unless --pin")
    if not args.candidate.exists():
        print(f"REJECT: candidate not found: {args.candidate}", file=sys.stderr)
        return 1

    rejects: list[str] = []

    # 1. immutable pins
    rejects += [f"immutable file changed — {b}" for b in check_pins()]

    original = SKILL.read_text(encoding="utf-8")
    fm_before, body_before = split_frontmatter(original)
    lines_before = original.splitlines()

    lo, hi = find_section(lines_before, args.section)
    if lo < 0:
        print(f"REJECT: section not found in SKILL.md: {args.section!r}", file=sys.stderr)
        return 1

    replacement = args.candidate.read_text(encoding="utf-8").rstrip("\n").splitlines()
    mutated_lines = lines_before[:lo] + replacement + lines_before[hi:]
    mutated = "\n".join(mutated_lines) + "\n"

    # 2. frontmatter byte-identical
    fm_after, _ = split_frontmatter(mutated)
    if fm_after != fm_before:
        rejects.append("frontmatter changed")

    # 3. anchor block verbatim
    def anchor_of(text: str) -> str | None:
        i, j = text.find(ANCHOR_START), text.find(ANCHOR_END)
        return text[i : j + len(ANCHOR_END)] if i >= 0 and j > i else None

    a_before, a_after = anchor_of(original), anchor_of(mutated)
    if a_before is None:
        rejects.append("anchor block missing from the ORIGINAL skill — repo is corrupt")
    elif a_after != a_before:
        rejects.append("anchor block missing or altered in the candidate")

    # 4 + 5. one hunk, in-section, size capped
    hunks, added, span = count_hunks(lines_before, mutated_lines)
    if hunks == 0:
        rejects.append("no change proposed")
    elif hunks > 1:
        rejects.append(f"{hunks} separate hunks; exactly 1 contiguous change allowed")
    if not (lo <= span[0] and span[1] <= hi):
        rejects.append(
            f"change touches lines {span[0]}-{span[1]}, outside section range {lo}-{hi}"
        )
    if added > MAX_ADDED_LINES:
        rejects.append(f"{added} lines added; cap is {MAX_ADDED_LINES}")
    growth = (len(mutated) - len(original)) / max(1, len(original))
    if growth > MAX_GROWTH:
        rejects.append(f"skill grew {growth:.1%}; cap is {MAX_GROWTH:.0%}")

    # 6. no new claims in the skill file itself
    sm = difflib.SequenceMatcher(None, lines_before, mutated_lines, autojunk=False)
    added_text = "\n".join(
        ln for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"
        for ln in mutated_lines[j1:j2]
    )
    for c in new_claims(added_text):
        rejects.append(f"new claim in skill text — {c}")

    if rejects:
        print("REJECTED", file=sys.stderr)
        for r in rejects:
            print(f"  - {r}", file=sys.stderr)
        return 1

    print(f"LEGAL: 1 hunk, +{added} lines, {growth:+.1%} size, section {args.section!r}")
    if args.apply:
        SKILL.write_text(mutated, encoding="utf-8")
        print(f"applied to {SKILL.relative_to(REPO)}")
    else:
        out = args.candidate.parent / "candidate-SKILL.md"
        out.write_text(mutated, encoding="utf-8")
        try:
            shown = out.relative_to(REPO)
        except ValueError:
            shown = out  # candidate staged outside the repo, print the absolute path
        print(f"dry run, candidate written to {shown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
