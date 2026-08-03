#!/usr/bin/env bash
# commit_run.sh — one commit per engine run, so every draft and every accepted
# mutation has a traceable point in history.
#
# Usage:
#   scripts/commit_run.sh draft   "msp-gap-friday-6pm"   # a drafting run
#   scripts/commit_run.sh improve "round-3-add-constraint"
#   scripts/commit_run.sh pain    "last30days-2026-07-29"
#
# Pushes to origin when a remote exists. Set ENGINE_NO_PUSH=1 to commit locally only.
# Never force pushes. Never rewrites history. If there is nothing to commit it
# says so and exits 0, so a no-change run does not look like a failure.

set -euo pipefail

KIND="${1:-run}"
LABEL="${2:-unlabelled}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

case "$KIND" in
  draft|improve|pain|doctrine|run) ;;
  *) echo "kind must be one of: draft improve pain doctrine run" >&2; exit 2 ;;
esac

if [ -z "$(git status --porcelain)" ]; then
  echo "nothing to commit (clean tree) — run recorded no changes"
  exit 0
fi

git add -A

# Human-readable summary of what this run touched, for the commit body.
CHANGED="$(git diff --cached --name-status | sed 's/^/  /')"
DRAFTS_TOUCHED="$(git diff --cached --name-only -- drafts/ | wc -l | tr -d ' ')"
SCORE_LINE=""
if [ "$DRAFTS_TOUCHED" -gt 0 ] && [ -f scripts/craft_score.py ]; then
  # Score every draft this run touched; a HARD failure is recorded, not hidden.
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    S="$(python3 scripts/craft_score.py "$f" --json 2>/dev/null \
         | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["score"] + (" HARD-FAIL" if d["hard_fail"] else ""))' \
         2>/dev/null || echo "unscored")"
    SCORE_LINE="${SCORE_LINE}
  $(basename "$f"): ${S}"
  done < <(git diff --cached --name-only -- drafts/)
fi

git commit -q -F - <<MSG
${KIND}: ${LABEL}

Run kind: ${KIND}
Label:    ${LABEL}

Files:
${CHANGED}
${SCORE_LINE:+
Craft scores:${SCORE_LINE}}

Nothing in this commit is published. Posting is a separate human action.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
MSG

SHA="$(git rev-parse --short HEAD)"
echo "committed ${SHA}: ${KIND}: ${LABEL}"

if [ "${ENGINE_NO_PUSH:-0}" = "1" ]; then
  echo "ENGINE_NO_PUSH=1 — not pushing"
  exit 0
fi

if git remote get-url origin >/dev/null 2>&1; then
  BRANCH="$(git rev-parse --abbrev-ref HEAD)"
  if git push -q origin "$BRANCH" 2>/dev/null; then
    echo "pushed ${SHA} to origin/${BRANCH}"
  else
    echo "push failed (offline, or no upstream yet). Commit is safe locally; run: git push -u origin ${BRANCH}" >&2
  fi
else
  echo "no origin remote yet — commit is local only"
fi
