---
name: trend-post
description: Use when the ask is a post about something trending, a news peg, a competitor launch, or "what should we post about this week" - finds candidate pegs, applies the standing gate, files briefs, then drafts and scores the ones that survive.
license: MIT
metadata:
  author: linkedin-post-engine
  version: "1.0"
---

# trend-post

Turn a trending thing into a post that this account has standing to write, or say
plainly that it does not and file nothing.

Most news posting fails the same way: the peg is real, the account has no reason to
speak on it, and the post reads as a company shouting near a headline. This skill
exists to make that failure loud and early instead of quiet and published.

## Non-negotiables

1. `CORE-LAWS.md` in `.claude/skills/post-drafter/` governs every draft this skill
   produces. It is not relaxed because a peg is hot.
2. The standing-gate law is the whole point of this skill. Before riding any peg,
   name a credible, non manufactured reason this account can speak on it. "It is
   about AI and we do AI" is manufactured relevance. Kill it.
3. A peg does not unlock a claim. Anything the news tempts you to say still has to
   be in `doctrine/VERIFIED-CLAIMS.md`, sourced, before it can appear in a body.
4. Nothing here posts. This skill files briefs and writes drafts.

## Step 1 · Find candidates

Pick the sources that fit what the account actually sells. For an ops product sold
to MSPs, funds and clinics, that is roughly:

- The ICP's own rooms, which are already listed with live URLs in
  `pain/PAIN-MATRIX.md`. A thread with 400 upvotes this week is a better peg than a
  vendor press release, because the room is already arguing about it.
- Vendor and platform announcements that change what the buyer's stack does.
- Regulatory or platform changes that alter what the buyer is allowed to do.

If a Leadshark MCP connection is available, `feed` and `list_signals` show what the
account's own network is reacting to right now. That is the highest signal source
available, because it is the room the post will actually land in.

Collect 5 to 10 candidates. Do not evaluate while collecting.

## Step 2 · Apply the standing gate, in writing

For each candidate, answer in one sentence: why can this account speak on this
credibly, without manufacturing the link?

Good answers look like: we sell the own-cloud version of exactly the thing that just
broke. We have been asked this question by four buyers this month. The incumbent
just published a price the room is angry about.

Bad answers, all of which mean drop it: it is about AI. It is trending. Our ICP
probably cares. We could tie it to our product.

Expect to drop most of them. Dropping eight of ten is a good run.

## Step 3 · File a brief for each survivor

```bash
python3 scripts/new_brief.py "<peg>" --url <source> --icp <slice> \
    --reason "<the standing-gate answer>"
python3 scripts/new_brief.py --list --open
```

A brief filed without `--reason` is marked UNANSWERED and is **not draftable**. That
is deliberate. It parks the idea without letting it become a post by momentum.

## Step 4 · Draft one brief

Load `.claude/skills/post-drafter/SKILL.md` and follow it exactly. The brief supplies
the peg and the standing reason. It does **not** supply the pain or the shape:

- Pain comes from `pain/PAIN-MATRIX.md`, in the ICP's own words, one per post.
- Shape comes from `doctrine/BODY-PATTERNS.md`, and must differ from the last shape
  that shipped.
- The peg belongs in the body as the reason to speak now, not as the whole post. A
  post that is only news is a post about somebody else's product.

Then score it and report honestly:

```bash
python3 scripts/craft_score.py drafts/<file>.md
```

## Step 5 · Close the loop

Write the outcome back into the brief: the draft filename, the score, or the
refusal and its reason. Then set `status:` to `drafted`, `refused` or `dropped`.

An inbox nobody closes becomes a list of things that felt urgent once.

## Refusing

The most common honest outcome of this skill is: "three pegs this week, none of
them clears the standing gate, here is what would". Say that. Do not manufacture a
link to fill a slot, and do not lower the bar because the calendar wants a post.
