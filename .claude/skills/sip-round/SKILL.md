---
name: sip-round
description: Use when running a self-improvement round on the post-drafter skill - executes draft, score, diagnose, mutate, rescore, accept-or-revert with a calibration gate and a git commit per run.
license: MIT
metadata:
  author: linkedin-post-engine
  version: "1.0"
---

# sip-round

One self-improvement round on the `post-drafter` skill. Ported from the
`self-improving-agent-skills` pattern (Executor / Analyst / Mutator), with the
three things that pattern is missing bolted on: a calibration gate before
anything runs, a hardened accept rule, and an immutable core.

Usage: `/sip-round [--rounds N] [--dry]`. Default 3 rounds, hard max 12.

## What this loop optimises, and what it refuses to

It optimises **craft compliance, truthfulness, and ICP fit.** Nothing else.

It does **not** optimise predicted reach. Predicting LinkedIn reach from text is
empirically dead: the source engine measured a blind LLM judge at Spearman 0.21
against real impressions, and an offline heuristic at **negative** 0.11. Northwind has
zero performance data anyway, so predicted reach is not merely unreliable here, it
is unavailable. Any future version that starts scoring predicted reach has
regressed, not improved.

## Step 0 — PRECHECK. Hard stop on failure.

```bash
python3 scripts/calibrate.py            # gold must pass, planted must all be caught
python3 scripts/apply_mutation.py --pin # pin the sha256 of every human-owned file
git rev-parse --abbrev-ref HEAD         # must NOT be main
git switch -c "sip/$(date +%Y-%m-%d)" 2>/dev/null || git switch "sip/$(date +%Y-%m-%d)"
```

If `calibrate.py` is not CALIBRATED, **stop and report.** Do not run the loop. A
scorer that rejects a human-certified draft, or that misses a planted violation, is
a broken fitness function, and optimising against it makes the skill worse while
the numbers go up.

Refuse to run on `main`. The loop edits a prompt; `main` is what humans invoke.

## Step 1 — BASELINE

For each of the 10 scenarios in `scenarios/scenarios.jsonl`, dispatch the
`drafter` subagent with that one scenario. Then score every draft:

```bash
python3 scripts/craft_score.py runs/<ts>/r0/*.md --json
```

Then dispatch `judge` once per draft for the 6 reading-comprehension checks.
**One judge call per draft, not per check.**

The drafter and the judge are separate agents with separate contexts, and the judge
never sees the drafter's reasoning. Upstream lets its executor grade its own output,
which is how a loop learns to satisfy itself instead of the rubric.

Round score:

```
draft_score    = 0.0 if any HARD/gate fail else (soft_passed / soft_total)
round_score    = mean(draft_score across the 10 scenarios)
gate_integrity = total gate fails across all scenarios      # must be 0 to accept
```

Two tiers, not one flat pass rate. Upstream sums every check into a single
percentage, which lets a mutation trade one truthfulness failure for two craft
passes and still be "kept". For a product account, one invented customer is a legal
problem, not a rounding error.

## Step 2 — DIAGNOSE

Dispatch `analyst` with the **full** `SKILL.md` and **every** failing check.
Upstream truncates its analyst to the first 2000 characters of the skill and the
first 5 failures, so it routinely diagnoses a file it has not finished reading.

Returns `{diagnosis, dominant_check, mutation_strategy, target_section, suggested_change}`.

If it returns `saturated`, **stop the loop.** Do not mutate. Upstream keeps
mutating after saturation because its analyst returns an "all passed" stub while
its mutator edits anyway, which is drift generated for free.

## Step 3 — MUTATE

Dispatch `mutator` with the analyst's JSON. It writes a replacement for one
named section. Then the script decides legality:

```bash
python3 scripts/apply_mutation.py --section "<target_section>" \
    --candidate runs/<ts>/rN/candidate-section.md
```

Six gates: immutable pins unchanged, frontmatter identical, anchor block verbatim,
one contiguous hunk inside the named section, at most 25 added lines and 15% growth,
and no new claims **in the skill file itself**.

That last one is the defence against the `add_example` trap. A plausible fake
specific baked into the prompt gets reproduced in every future draft forever, and it
reads as credible precisely because it is specific.

A reject costs nothing further: no re-score, no tokens spent on the round.

## Step 4 — RESCORE

Repeat step 1 against the candidate skill.

## Step 5 — DECIDE. Four conditions, all required.

Accept only if **every** one holds:

1. `gate_integrity == 0` — zero gate fails across all 10 scenarios. A gate fail
   vetoes regardless of craft gain.
2. `craft_delta >= 1` **whole check**, not a percentage. With 10 scenarios the
   per-check resolution is under 1%, and a sub-check delta is judge noise.
3. **No scenario regressed** on any check it previously passed. This blocks the
   trade where three scenarios gain and one collapses.
4. A **confirm re-score reproduces the gain.** Upstream samples once, and one
   sample of a multi-check LLM judge is not a measurement.

Upstream's rule is `kept = new_pct > baseline_pct`. That is one noisy sample
against another.

Fail any condition → REVERT. The candidate is discarded, `SKILL.md` is untouched,
and the rejected diff is archived to `runs/<ts>/rN/rejected-diff.patch`.

## Step 6 — RECORD

```bash
bash scripts/commit_run.sh improve "r<N>-<strategy>-<kept|rejected>"
```

Append to `CHANGELOG.md`: run id, round, strategy, target section, the analyst's
diagnosis verbatim, the diff, the per-check before/after table, the confirm-rescore
result, and the commit sha. Rejected mutations get a one-line entry in a separate
`## Rejected` section — a strategy that keeps getting rejected is itself a finding.

Commit on every run, even when every mutation was rejected. The archive is the point.

## Step 7 — STOP

Stop on any of: target pass rate reached, analyst reports saturated, **2
consecutive rejects**, round budget exhausted, or any gate-fail regression.

## Step 8 — SLATE

Write `runs/<ts>/slate.md`: every compliant draft, best craft score first, with its
blocking failures listed if any. This is what a human reads.

## The human gate, stated plainly

The loop may write: `runs/**`, `CHANGELOG.md`, and `SKILL.md` + `references/` —
but only mutable sections, only via `apply_mutation.py`, only on an accepted round,
only on branch `sip/<date>`.

The loop may only **propose**, into `proposals/`: `CORE-LAWS.md`,
`doctrine/VERIFIED-CLAIMS.md`, `pain/PAIN-MATRIX.md`,
`doctrine/VOICE-PROFILE-founder.md`, and `scenarios/scenarios.jsonl`.

**Merging `sip/<date>` into `main` is the human gate.** The loop evolves the drafter
on a branch; the version anyone actually invokes lives on `main` and moves only when
a person has read the changelog and the diff.

Nothing in this repo publishes to LinkedIn. There is no API call, and adding one is
out of scope by law, not by omission.

## Honest limits

- **Goodhart risk is real and deliberately re-opened.** The source engine's offline
  optimiser explicitly refused to auto-evolve its drafter, to avoid optimising
  against its own rule-checker. This loop does evolve it, which is only defensible
  because of the immutable core, the four-part accept rule, and the branch gate.
  Those slow the failure mode; they do not remove it. **The only real detector is a
  human cold-reading 5 random slate drafts once a month.** Put it in the calendar.
- **6 of the checks are LLM-judged**, so genuine small gains are indistinguishable
  from judge noise. The whole-check delta buys resistance at the cost of
  sensitivity, and the loop will plateau early. That is the right trade here.
- **With zero performance data, the human's taste IS the fitness function.** The
  gold exemplars are winners by declaration. The loop converges on the stated craft
  standard and structurally cannot discover that the standard is wrong.
- **On day one, distribution is the binding constraint, not draft quality.** A
  product account with no followers gets no reach regardless of how good the copy
  is. This loop improves drafts. It does not build an audience.
