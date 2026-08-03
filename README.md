# linkedin-post-engine

A drafting harness for LinkedIn posts written on behalf of somebody else, built so it
cannot quietly lie about them.

It drafts, scores and refuses. **It never publishes.** There is no LinkedIn API call
anywhere in it, and adding one is out of scope by law rather than by omission.

The interesting part is not the drafting. Any model drafts. The interesting part is
that a claim which is not in the client's allowlist cannot reach a post, and the gate
that enforces that is itself calibrated against planted violations on every run.

## Why it exists

Content written for a client fails in one of two ways. It sounds like the agency
instead of the client, or it says something the client cannot stand behind. Both are
invisible at drafting time and expensive after publication.

So this repo splits the problem:

- **`doctrine/`** is the client's truth boundary and voice, owned by a human.
- **`scripts/`** is the gate, owned by the engine, identical for every client.
- **`drafts/`** is output. Nothing is a draft until it lives there.

The scorer runs 27 checks. HARD checks block a draft outright and the optimiser may
not touch them: unsourced money, unsigned-off company names, invented scarcity,
certification claims, borrowed cadence, skeleton reruns, disproved claims, artifact
promises with nothing to deliver. SOFT checks are craft mechanics and lower the score.

## Setup

```bash
git clone <this repo> && cd linkedin-post-engine
cp doctrine/VERIFIED-CLAIMS.template.md doctrine/VERIFIED-CLAIMS.md
cp doctrine/VOICE-PROFILE.template.md  doctrine/VOICE-PROFILE-founder.md
cp doctrine/config.example.json        doctrine/config.json
cp pain/PAIN-MATRIX.template.md        pain/PAIN-MATRIX.md
python3 scripts/init_ledger.py --show     # creates engine.db
python3 scripts/calibrate.py              # must print CALIBRATED
```

Python 3.10+ and sqlite3. No API keys, no network calls, no dependencies.

Then fill in the four files you just copied. Until you do, the engine is honest and
useless, which is the correct order.

## The five laws

1. **Nothing auto-posts.** This repo drafts, scores and commits.
2. **A claim not in `doctrine/VERIFIED-CLAIMS.md` does not go in a post.** A vaguer
   version of an unsourced claim is still unsourced.
3. **`.claude/skills/post-drafter/CORE-LAWS.md` is immutable.** The optimiser verifies
   its sha256 before and after every mutation.
4. **The scorer runs on every draft, before handover.** Report blockers honestly and
   never resolve a HARD failure by laundering the claim.
5. **`scripts/calibrate.py` must be CALIBRATED before the optimiser runs.**

## Daily use

```bash
python3 scripts/craft_score.py drafts/my-post.md    # score one draft, exit 1 on HARD fail
python3 scripts/calibrate.py                        # the gate
python3 scripts/new_brief.py "<trending peg>" --icp smb --reason "<standing gate>"
python3 scripts/new_brief.py --list --open
python3 scripts/ingest_voice.py posts.json --name "Jane Doe" --slug founder
bash    scripts/commit_run.sh draft "<label>"
```

With Claude Code, the skills in `.claude/skills/` load themselves:

- **`post-drafter`** — draft one post from one pain, in one shape, with one keyword.
- **`trend-post`** — turn trending pegs into briefs, apply the standing gate, then draft.
- **`sip-round`** — the self-improvement loop, gated on calibration being green.

## Voice, measured not imagined

`scripts/ingest_voice.py` takes a JSON export of the account's real posts and writes a
profile from counted values: length distribution, sentence rhythm, share of sentences
under eight words, emoji per post, hashtag habit, person, closer style, and a
performance table ranked by reactions.

It exists because "write in their voice" is otherwise a vibe. If the account's longest
post ever is 270 words, the config says `words_max: 270`, and the scorer stops you
writing a 430 word post they would never have published.

The pull itself is an agent step with its own auth, not a function in this repo. Any
source works as long as it produces `[{"text": ..., "reactions": ...}, ...]`.

## Client config

`doctrine/config.json` holds everything that differs per account: word range, emoji
ceiling, hook length, arrow count, brand-name ceiling, banned vocabulary, disproved
claims, borrowed cadence signatures, the differentiator markers, and the vendor and
role vocabularies used by the entity gate.

Three deliberate properties: an unknown key is a hard error, a malformed file is a hard
error, and no config value can turn a HARD check into a SOFT one. Config tunes
thresholds. It cannot disarm a gate.

## Calibration

```
GOLD passing:    2/2
PLANTED caught:  11/11
RESULT: CALIBRATED
```

Two hand-certified drafts must pass with zero HARD failures, and eleven planted
violations must each be caught **by the correct check id**. Catching a fabricated
customer via the dash check is a failure, not a pass, because it means the right check
is asleep and something else happened to fire.

Run it after any change to the scorer or the config. If it is not green, nothing
downstream can be trusted.

## What this will not do for you

- It will not publish, schedule or automate posting.
- It will not keep your allowlist true. Products change; a human re-checks the source.
- It will not refresh the pain corpus. Quotes go stale, and stale quotes stop sounding
  like the room.
- It will not learn what performs unless you mark rows `posted` with a date in the
  ledger. Leave every row as a draft and the rotation and keyword-freshness gates pass
  by default rather than by merit.

## Licence

MIT. See `LICENSE`.
