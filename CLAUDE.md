# CLAUDE.md — repo law

A drafting harness for LinkedIn posts written on behalf of a client account.

Self serve: this repo does not read from, write to, or depend on any other content
engine. Everything client specific lives in `doctrine/` and `pain/`.

## The five laws

1. **Nothing auto-posts.** This repo drafts, scores and commits. There is no LinkedIn
   API call anywhere in it, and adding one is out of scope by law.
2. **A claim not in `doctrine/VERIFIED-CLAIMS.md` does not go in a post.** No
   exceptions. A vaguer version of an unsourced claim is still unsourced.
3. **`.claude/skills/post-drafter/CORE-LAWS.md` is immutable.** The optimiser verifies
   its sha256 before and after every mutation.
4. **The scorer runs on every draft, before handover.** `python3
   scripts/craft_score.py <draft>`. Report the blockers honestly; never resolve a HARD
   failure by laundering the claim.
5. **`scripts/calibrate.py` must be CALIBRATED before the optimiser runs.**

## Layout

```
doctrine/     the truth boundary and craft rules (human owned)
  VERIFIED-CLAIMS.md      the allowlist. THE most important file here
  VOICE-PROFILE-*.md      whose voice this is, measured
  config.json             per client thresholds and vocabularies
  PATTERNS.md             learnings ledger, tiered
  BODY-PATTERNS.md        the shape cards
  ARTIFACTS.md            what a CTA may promise
pain/         PAIN-MATRIX.md — ICP pains in their own words, with source URLs
briefs/       the task inbox, one file per task
drafts/       the posts. One door. Nothing is a draft until it lives here
scenarios/    the frozen exam. The loop may NOT write this
fixtures/     gold/ + planted/ — the calibration gate
scripts/      craft_score, calibrate, apply_mutation, init_ledger, ingest_voice,
              new_brief, commit_run
engine.db     lifecycle ledger + mutation log
```

## Commands

```bash
python3 scripts/init_ledger.py --show          # ledger schema + row counts
python3 scripts/craft_score.py drafts/*.md     # score. exit 1 = HARD failure
python3 scripts/calibrate.py                   # the gate. must be green
python3 scripts/new_brief.py --list --open     # the task inbox
python3 scripts/ingest_voice.py posts.json --name "<name>"
bash scripts/commit_run.sh draft "<label>"     # commit + push this run
```

Ledger is `ALTER TABLE ADD COLUMN` only, via `init_ledger.py`, which backs up first.

## Drafting

Read in this order, every time: `CORE-LAWS.md`, `VERIFIED-CLAIMS.md`,
`VOICE-PROFILE-*.md`, `PATTERNS.md`, `BODY-PATTERNS.md`, `PAIN-MATRIX.md`.

One pain, one shape, one CTA keyword. No two consecutive posts share a shape. Length
and emoji ceiling come from `config.json`, which comes from the measured voice profile.
Close with one plain prose ask, not a numbered emoji ladder, unless the profile shows
they actually write ladders.

## Refusing a brief

Some briefs ask for what the laws forbid. Do not comply and do not return nothing.
Reshape to the nearest honest post and state the refusal in a trailing comment.

A draft that invents a customer to satisfy a brief is the worst thing this repo can
produce. `fixtures/gold/gold-02-refusal.md` is a worked example of refusing well.

## Token frugality

Grep to locate, read the region. Query the ledger with `sqlite3`, never dump it.
