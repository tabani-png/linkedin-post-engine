# BODY-PATTERNS.md — the shape shelf

A shape is the full hook, body and close structure. P-012 governs the shelf: **no two
consecutive posts share a shape.** Record the card in the draft frontmatter and in the
ledger `shape` column.

**Objective first, then the card.** Reach and signups come from different shapes.

---

## Card 1 · challenge-belief  ← the conversion default

**Objective: qualified DMs and signups.**

1. Line one attacks ONE trusted belief the buyer holds.
2. A runnable TEST with named roles, not a claim. The reader can run it themselves.
3. The JUDGE: a reframe that resets the frame.
4. Soft CTA.

Requires no receipts, no artifact and no prestige brand, which is why it works for an
account with no published proof yet.

## Card 2 · pattern-interrupt (mistake-as-enemy)

**Objective: self-defence comments, quality DMs. The cheapest credible shape for an
account with no history.**

"Most [role] did X. That is the mistake." Then implicate the reader, then teach the fix.

Also the safe way to handle an incumbent your channel resells: attack the belief, not
the product line.

## Card 3 · single-incumbent-bury  ← reach only

**Objective: reach and in-room visibility. Do not expect it to convert.**

Bury ONE named incumbent the ICP pays for, state the replacement claim, add a cost
ladder, keep the language in-room. Read B-009 before using it.

## Card 4 · teach-a-tactic

**Objective: depth and objection data.**

Give ONE genuinely useful tactic inside the body, then ask softly. Never gate the value.
The tactic must be runnable **without your product**.

## Card 5 · grouped-mandate (bundle)

**Objective: reach plus DMs. One dense outing, then rotate off. Never a workhorse.**

Hook, frame, one enemy with a cost, five to seven buckets where each bucket is a
category **plus the concrete painful moment removed**, a sovereignty or differentiator
line, a reframe close. A bucket that is only a label is a dead bucket. The artifact CTA
stays blocked until something is marked live in `ARTIFACTS.md`.

---

## Cards to keep blocked until you have earned them

| Shape | Unlock condition |
|---|---|
| **story-proof** | A real run on real data with a real failure the author caught. Only the person who lived it can speak it, in their own words. |
| **live-artifact** | The promised artifact exists and is marked live. |
| **first-person-build** | The poster actually built the thing, with a verifiable cost basis. Unavailable to a partner or reseller account. |
| **booster graft** | Roughly ten measured posts on this account, so there is a real prior winner to graft onto. |
| **question / news** | Conditional, not blocked. Needs a standing, non manufactured reason to speak on the peg. |

---

## Rotation

With five live cards and a no-consecutive-repeat rule, an honest cadence looks like:
challenge-belief, pattern-interrupt, challenge-belief, teach-a-tactic,
single-incumbent-bury, challenge-belief, grouped-mandate.

Check what shipped last before picking:

```bash
sqlite3 engine.db "SELECT filename, shape, posted_at FROM drafts WHERE status='posted' ORDER BY posted_at DESC LIMIT 3;"
```

If that query returns nothing, the rotation gate is passing by default rather than by
merit. Mark posts as posted or the shelf is decorative.
