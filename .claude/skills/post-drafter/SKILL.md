---
name: post-drafter
description: Use when drafting a LinkedIn post for one client account, lead generation - loads the claims allowlist, pain matrix, shape shelf and craft laws, then drafts one post and scores it.
license: MIT
metadata:
  author: linkedin-post-engine
  version: "1.0"
---

# post-drafter

Draft one LinkedIn post for Northwind, from one pain, in one shape, with one CTA
keyword. Then score it and report what blocks it.

<!-- ANCHOR:start — verbatim block, apply_mutation.py rejects any change to it -->
## Non-negotiables

1. `CORE-LAWS.md` in this directory is included by reference and governs every
   draft. L1 to L8 are not subject to interpretation, tuning, or improvement.
2. Every claim must be in `doctrine/VERIFIED-CLAIMS.md`. If it is not there, it
   does not go in the post. A vaguer version of an unsourced claim is still
   unsourced.
3. The own-cloud beat is Northwind's only structural differentiator. A draft that
   removes it entirely is a worse draft, and no mutation may remove this line.
4. Nothing in this repo publishes. Drafting is not posting.
<!-- ANCHOR:end -->

## Load order

Read these before writing a word. The order matters: laws first, so that
everything after is filtered through them.

1. `CORE-LAWS.md` — the six truthfulness laws plus L7 and L8.
2. `doctrine/VERIFIED-CLAIMS.md` — the allowlist. This is the boundary of what is
   sayable.
3. `doctrine/VOICE-PROFILE-founder.md` — whose voice this is. If it still says
   UNVERIFIED, every draft you produce is craft-compliant and voice-unverified, and
   you must say so on handover.
4. `doctrine/PATTERNS.md` — obey every LAW and BURNED entry.
5. `doctrine/BODY-PATTERNS.md` — the five shape cards.
6. `pain/PAIN-MATRIX.md` — the ICP's own words.

## Pain selection

One pain per post, named before drafting (P-019). Never recycle a pain while a post
on it is under 7 days old.

Use the ICP's own phrasing from the pain corpus. A pain described in your words
instead of theirs is the difference between a post that gets recognised and a post
that gets scrolled. Prefer a verbatim phrase from the corpus in or near the hook.

Check what is still fresh:

```bash
sqlite3 engine.db "SELECT pain_category, MAX(posted_at) FROM drafts WHERE status='posted' GROUP BY pain_category;"
```

## Shape selection

One shape per post from `doctrine/BODY-PATTERNS.md`. **No two consecutive posts
share a shape** (P-012). Sameness, not topic, causes the reach cliff.

Pick by objective, not by taste:

- Pilot signups and qualified DMs → `challenge-belief`. This is the default,
  because at the source engine every measured booking came from this shape.
- Cheap credibility with no receipts → `pattern-interrupt`.
- Reach at scale → `single-incumbent-bury`. Read the B-009 hazard first: MSPs
  resell M365, so burying Copilot points at Northwind's own channel.
- Depth and objection data → `teach-a-tactic`.
- One dense outing, then rotate off → `grouped-mandate`.

Four shapes are blocked outright today (story-proof, live-artifact,
first-person-build, booster-graft). `doctrine/BODY-PATTERNS.md` says why for each.
Do not reach for them.

Check the last shape used:

```bash
sqlite3 engine.db "SELECT filename, shape, posted_at FROM drafts WHERE status='posted' ORDER BY posted_at DESC LIMIT 3;"
```

## Drafting

Draft 5 hooks. Ship the painfully obvious one.

Body: pain-first, 220 to 320 words before the CTA (P-023). Open on concrete lived
pain scenes before any product mention. A hook plus a list is a rejected draft.

Mechanics, all enforced by the scorer:

- No hyphens, no em dashes. Commas and full stops.
- One idea per line. Hard returns, not paragraphs.
- Arrows: `→ [Verb] [outcome] like [a real role]`. Between 4 and 6. The reader
  bounces at arrow 7. A vague tier kills the arrow.
- One enemy. Multi-enemy is no enemy.
- At most 3 named brands in the whole body. The 11-integration list is the trap.
- A cost ladder is exactly 3 lines, or absent.
- CTA is 4 separate lines plus a P.S. Never mashed onto one line.
- One unique uppercase CTA keyword, quoted once, unused in 14 days.
- No banned vocabulary: synergy, leverage, unlock, transformation, journey,
  cutting-edge, seamless, supercharge.

## Refusing a brief

Some briefs ask for something the laws forbid: a customer win when no customer may
be named, a head-to-head comparison when both-sides framing is banned.

Do not comply and do not return nothing. Reshape the brief into the nearest honest
post, then state what you refused and why in a trailing HTML comment.

A draft that invents a customer to satisfy a brief is the worst thing this skill
can produce. Refusing correctly is a pass.

## Output and self-check

Write one file to `drafts/<YYYY-MM-DD>-<slug>.md` with full frontmatter:

```
<!--
persona: founder | pilot-customer | partner
icp: msp | fund-family-office | healthcare | smb
pain: <row id>
shape: <card name>
keyword: <UPPERCASE>
-->
```

Then score it and report honestly:

```bash
python3 scripts/craft_score.py drafts/<file>.md
```

Fix mechanical failures. **Never resolve a HARD failure by hiding the claim** —
rewording an invented figure into a vaguer invented figure, or deleting the word
that triggered a check while keeping the assertion. If a claim is blocked, cut it
and say in your handover that it was cut and what would unblock it.

Report the score, the blocking failures, and what a human needs to supply. A
blocked draft honestly reported is a good outcome. A passing draft that got there
by laundering a claim is a failure of this skill.
