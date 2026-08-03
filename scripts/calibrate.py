#!/usr/bin/env python3
"""
calibrate.py — the gate. Nothing in the loop runs unless this is green.

Two questions, and both must be yes:

  1. Do the hand-certified GOLD drafts pass with zero HARD failures?
     If the scorer rejects a draft a human has certified as good, the scorer is
     wrong and any optimisation run on top of it optimises toward a broken target.

  2. Is every PLANTED violation caught, by the CORRECT check id?
     Catching a fabricated customer via the dash check is not a pass. It means the
     right check is asleep and something else happened to fire.

Borrowed wholesale from the upstream engine's own calibration convention, which
gates its offline optimiser on `WINNERS compliant: 10/10` and
`PLANTED BURNED caught: 6/6` before it is allowed to propose anything.

Each fixture declares what it is for in its frontmatter:

    expect: PASS
    expect_fail: C-MONEY
    env: ENGINE_ARTIFACTS=fixtures/doctrine/ARTIFACTS-empty.md

Usage:
  python3 scripts/calibrate.py            # run the gate
  python3 scripts/calibrate.py -v         # show every check, not just failures

Exit codes: 0 = CALIBRATED, 1 = NOT CALIBRATED, 2 = no fixtures found.
"""

from __future__ import annotations

import argparse
import importlib
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "fixtures"
GOLD = FIXTURES / "gold"
PLANTED = FIXTURES / "planted"
FIXTURE_DOCTRINE = FIXTURES / "doctrine"
EMPTY_DIR = FIXTURES / "_empty"

sys.path.insert(0, str(REPO / "scripts"))


def fm_field(text: str, key: str) -> str | None:
    m = re.match(r"\s*<!--(.*?)-->", text, re.S)
    if not m:
        return None
    hit = re.search(rf"^\s*{key}\s*:\s*(.+?)\s*$", m.group(1), re.M | re.I)
    return hit.group(1).strip() if hit else None


def score_fixture(path: Path, verbose: bool) -> list:
    """Score one fixture under its declared environment, in a fresh module import.

    craft_score reads its paths at import time, so the module is reloaded per
    fixture. That is the price of keeping the live scorer free of runtime config.
    """
    text = path.read_text(encoding="utf-8")

    env = {
        "ENGINE_CLAIMS": str(FIXTURE_DOCTRINE / "VERIFIED-CLAIMS.md"),
        "ENGINE_VOICE": str(FIXTURE_DOCTRINE / "VOICE-PROFILE-founder.md"),
        "ENGINE_ARTIFACTS": str(FIXTURE_DOCTRINE / "ARTIFACTS.md"),
        "ENGINE_DRAFTS_DIR": str(EMPTY_DIR),
        "ENGINE_LEDGER": str(FIXTURE_DOCTRINE / "no-such-ledger.db"),
    }
    override = fm_field(text, "env")
    if override:
        for pair in override.split():
            k, _, v = pair.partition("=")
            env[k] = str(REPO / v) if not v.startswith("/") else v

    saved = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        import craft_score
        importlib.reload(craft_score)
        checks = craft_score.run_checks(path, craft_score.load_claims())
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    if verbose:
        for c in checks:
            mark = "ok  " if c.passed else ("HARD" if c.klass == "HARD" else "soft")
            print(f"      [{mark}] {c.id}")
    return checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    EMPTY_DIR.mkdir(parents=True, exist_ok=True)
    (EMPTY_DIR / ".gitkeep").touch()

    gold = sorted(GOLD.glob("*.md"))
    planted = sorted(PLANTED.rglob("*.md"))
    if not gold or not planted:
        print(f"no fixtures: {len(gold)} gold, {len(planted)} planted", file=sys.stderr)
        return 2

    failures: list[str] = []

    print(f"GOLD — {len(gold)} human-certified drafts must pass with zero HARD failures")
    gold_ok = 0
    for f in gold:
        checks = score_fixture(f, args.verbose)
        hard = [c for c in checks if c.klass == "HARD" and not c.passed]
        if hard:
            failures.append(f"gold {f.name} HARD-failed: " + ", ".join(c.id for c in hard))
            print(f"  FAIL  {f.name}  ({', '.join(c.id for c in hard)})")
            for c in hard:
                print(f"          {c.id}: {c.detail}")
        else:
            gold_ok += 1
            soft = sum(1 for c in checks if c.klass == "SOFT" and not c.passed)
            print(f"  pass  {f.name}  ({soft} soft misses)")

    print(f"\nPLANTED — {len(planted)} violations must each be caught by the RIGHT check")
    planted_ok = 0
    for f in planted:
        want = fm_field(f.read_text(encoding="utf-8"), "expect_fail")
        if not want:
            failures.append(f"planted {f.name} declares no expect_fail")
            print(f"  FAIL  {f.name}  (no expect_fail declared)")
            continue
        checks = score_fixture(f, args.verbose)
        fired = {c.id for c in checks if not c.passed}
        if want in fired:
            planted_ok += 1
            print(f"  caught  {f.name}  -> {want}")
        else:
            failures.append(
                f"planted {f.name} expected {want}, fired instead: {sorted(fired) or 'nothing'}"
            )
            print(f"  MISSED  {f.name}  expected {want}, fired {sorted(fired) or 'nothing'}")

    print(f"\nGOLD passing:    {gold_ok}/{len(gold)}")
    print(f"PLANTED caught:  {planted_ok}/{len(planted)}")

    if failures:
        print("\nRESULT: NOT CALIBRATED")
        print("The loop must not run. Fix the scorer or the fixtures first.")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("\nRESULT: CALIBRATED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
