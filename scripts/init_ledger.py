#!/usr/bin/env python3
"""
init_ledger.py — create or additively migrate engine.db, the lifecycle ledger.

Schema is a deliberate subset of the proven upstream ledger so the two stay
comparable, plus the columns this engine needs. Migration is ALWAYS additive:
`ALTER TABLE ADD COLUMN` only, never a rewrite, never a drop. Existing rows are
never touched.

Usage:
  python3 scripts/init_ledger.py            # create or migrate
  python3 scripts/init_ledger.py --show     # print schema + row counts
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "engine.db"

# column name -> SQL type/default. Add to this list to migrate; never edit or remove.
COLUMNS: list[tuple[str, str]] = [
    ("filename", "TEXT NOT NULL"),
    ("title", "TEXT"),
    ("persona", "TEXT"),              # founder | pilot-customer | partner — who posts it
    ("icp", "TEXT"),                  # msp | fund-family-office | healthcare | smb
    ("pain_category", "TEXT"),        # one row from pain/PAIN-MATRIX.md
    ("shape", "TEXT"),                # one shape from doctrine/BODY-PATTERNS.md
    ("keyword", "TEXT"),              # unique CTA keyword, no reuse < 14d
    ("status", "TEXT DEFAULT 'draft'"),   # draft | approved | posted | killed
    ("posted_at", "TEXT"),
    ("linkedin_url", "TEXT"),
    ("performance", "TEXT"),          # imp=<n>;comments=<n>;icp_pct=<n>;pilot_requests=<n>
    ("marked_good", "INTEGER DEFAULT 0"),
    ("learnings_ref", "TEXT"),        # the PATTERNS.md rule id this post proved
    ("craft_score", "TEXT"),          # "17/17" from scripts/craft_score.py
    ("hard_fail", "INTEGER DEFAULT 0"),
    ("pain_evidence", "TEXT"),        # source URL the pain was mined from
    ("commit_sha", "TEXT"),           # the commit that carried this draft
    ("notes", "TEXT"),
    ("created_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
    ("updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
]


def connect() -> sqlite3.Connection:
    return sqlite3.connect(LEDGER)


def create(con: sqlite3.Connection) -> None:
    cols = ",\n  ".join(f"{name} {decl}" for name, decl in COLUMNS)
    con.execute(f"CREATE TABLE IF NOT EXISTS drafts (\n  id INTEGER PRIMARY KEY,\n  {cols}\n)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_drafts_keyword ON drafts(keyword)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_drafts_posted ON drafts(posted_at)")
    # The mutation log for the self-improvement loop. One row per accepted or
    # reverted mutation, so a bad round is always traceable and reversible.
    con.execute("""
        CREATE TABLE IF NOT EXISTS mutations (
          id INTEGER PRIMARY KEY,
          run_id TEXT NOT NULL,
          round INTEGER NOT NULL,
          target_file TEXT NOT NULL,
          strategy TEXT,               -- add_example | add_constraint | restructure | add_edge_case
          diagnosis TEXT,              -- the Analyst's root cause
          change_summary TEXT,
          baseline_rate REAL,
          new_rate REAL,
          decision TEXT,               -- accepted | reverted
          commit_sha TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()


def migrate(con: sqlite3.Connection) -> list[str]:
    existing = {r[1] for r in con.execute("PRAGMA table_info(drafts)")}
    added = []
    for name, decl in COLUMNS:
        if name not in existing:
            # NOT NULL without default cannot be added to a populated table; relax it.
            safe = decl.replace(" NOT NULL", "")
            con.execute(f"ALTER TABLE drafts ADD COLUMN {name} {safe}")
            added.append(name)
    con.commit()
    return added


def show(con: sqlite3.Connection) -> None:
    for table in ("drafts", "mutations"):
        try:
            n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.Error:
            print(f"{table}: missing")
            continue
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
        print(f"{table}: {n} rows, {len(cols)} columns")
        print("  " + ", ".join(cols))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    fresh = not LEDGER.exists()
    if not fresh and not args.show:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(LEDGER, LEDGER.with_name(f"engine.db.bak-migrate-{stamp}"))

    con = connect()
    if args.show:
        show(con)
        con.close()
        return 0

    create(con)
    added = migrate(con)
    print(f"ledger {'created' if fresh else 'migrated'}: {LEDGER}")
    if added:
        print("added columns: " + ", ".join(added))
    show(con)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
