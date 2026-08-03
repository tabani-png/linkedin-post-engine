# CORE-LAWS.md — IMMUTABLE

The self-improvement loop cannot edit this file. `scripts/apply_mutation.py`
verifies its sha256 before and after every mutation and hard-stops on any change.
A loop that can edit its own laws has no laws.

Six truthfulness laws. Each maps to a gate check that blocks a draft outright.

---

## L1 · No invented customer

Northwind's site names **zero** business customers, zero case studies, and zero result
numbers. Therefore any organisation framed as a Northwind customer, pilot participant,
or user is fabricated *by construction* — there is no source to get it right from.

Naming an allowlisted integration, or the named incumbent, is not a customer claim.

Gate: `C-ENTITY`, `J-CUSTOMER`.

## L2 · Every number traceable

Every dollar figure, percentage, multiple, and quantity must appear in
`doctrine/VERIFIED-CLAIMS.md` with a source and a check date.

A vaguer version of an unsourced number is still an unsourced number. "Six figures
of ops cost" is not an improvement on an invented "$250K"; it is the same
fabrication with the evidence hidden.

Gate: `C-MONEY`.

## L3 · No fabricated testimonial voice

No quoted span and no attribution construction ("one MSP owner told us", "a COO we
work with") unless those exact words are in `pain/PAIN-MATRIX.md` with a live
source URL.

This law is why a pilot-customer-voice post may never be published from Northwind's own
account. The underlying story can be completely true and the post is still a
fabricated testimonial, because the speaker is not the poster. If a pilot customer
wants to speak, they write their own first draft in their own words and we edit
mechanics only.

Gate: `C-PERSONA`, `J-TESTIMONIAL`.

## L4 · No unreal scarcity

Scarcity is sayable only in the form the site publishes: `Early access · limited
pilot seats`. No numeric seat count, no deadline, no countdown, unless a real
figure is allowlisted.

"We are opening a small number of pilot seats" and "when the round fills" are
inventions layered on top of a sourced phrase. Inflated scarcity is the same class
of violation as an invented customer.

Gate: `C-SCARCITY`.

## L5 · Capability claims map to the allowlist

Every product-capability sentence must map to the sourced capability set in
`doctrine/VERIFIED-CLAIMS.md`.

**Architecture is not certification.** Own-cloud deployment is a published
architecture claim and is sayable. SOC 2, HIPAA, ISO, BAA, and PHI handling are
certification claims, the site makes none of them, and implying one is the single
most damaging output this engine could produce. The buyers most drawn to the
own-cloud story — fund COOs, healthcare ops — are exactly the ones who will check.

Gate: `J-CAPABILITY`.

## L6 · No stage inflation

Northwind sells early access and a waitlist. No implication of general availability,
funding, headcount, customer counts, growth stats, or "since our launch".

Gate: `J-STAGE`.

---

## Two more laws that are not truthfulness but are still immutable

## L7 · No borrowed cadence

This engine was ported from another operator's account. Their signature lines,
tics, and reframes may not appear in a Northwind post. The ported voice DNA is a craft
standard, not a voice.

Gate: `C-BORROWED`.

## L8 · Nothing auto-posts

This repo drafts, scores, and commits. It never publishes. There is no LinkedIn
API call anywhere in it, and adding one is out of scope by law, not by omission.
Every post is a human decision.
