# VERIFIED-CLAIMS.md — the allowlist that makes a claim sayable

`scripts/craft_score.py` reads this file. A dollar figure, a named company or a
scarcity claim that is **not listed here is a HARD failure** and the draft is blocked.
That is the point: the default answer to "can we say this?" is no.

Nothing is added from memory or inference. Every line carries a source and the date it
was checked, or the words "founder sign-off" plus a date.

## Line formats the scorer parses

Lines inside a fenced code block are documentation, not data, so this example block
allowlists nothing.

```
money: $30 a seat a month | <source url> | <YYYY-MM-DD>
entity: Acme Corp | founder sign-off <YYYY-MM-DD>
scarcity_phrase: limited pilot seats
pilot_seats: 8
```

`money:` allowlists every `$` figure on the line. `entity:` allowlists a named company.
`scarcity_phrase:` allowlists one exact scarcity wording. `pilot_seats:` is an integer
and is the only thing that unlocks a *numeric* seat claim.

---

## Source of truth

State here which page you scraped, on what date, and what it does **not** contain.
That second half is the load bearing part. If the site names zero customers, then any
customer claim is invented by construction and there is nothing to cite.

## money — verified figures

- money: <figure> | <source url> | <YYYY-MM-DD>

## entity — companies cleared to name

- entity: <company> | <source url or founder sign-off> | <YYYY-MM-DD>

## scarcity — the only sayable form

- scarcity_phrase: <exact wording the client publishes> | <source url> | <YYYY-MM-DD>

No `pilot_seats:` line unless a real count is published. Without it, every numeric seat
claim stays blocked.

## capability claims — the sourced set

Quote the client's own published capability wording verbatim. A capability sentence
outside this set is a fabrication.

**Architecture is not certification.** Deployment topology is an architecture claim.
SOC 2, HIPAA, ISO, BAA and PHI handling are certification claims. Blurring the two is
the single most damaging output this engine can produce, because the buyers most drawn
to the architecture story are exactly the ones who will check.

## Standing bans (never allowlistable)

- Invented customers, logos, testimonials or result numbers.
- Revenue, headcount, funding or customer-count figures the client does not publish.
- Any implication of a certification the client does not hold.
- General-availability language when the client sells early access or a waitlist.
- A customer-voice post published from the client's own account. That is a fabricated
  testimonial regardless of how true the underlying story is.
