#!/usr/bin/env python3
"""
craft_score.py — mechanical craft-compliance scorer for Northwind LinkedIn drafts.

This is the script-enforceable half of the fitness function. It answers one
question per check, always binary, never a vibe: does this draft violate a rule
we can prove it violates by reading the text?

It deliberately does NOT try to predict reach. Predicting LinkedIn reach from
text is empirically dead (blind-judge Spearman 0.21 on the upstream engine's own
labelled corpus), so this scorer optimises the one reliable text signal —
compliance with laws earned from real posts — and leaves outcome learning to a
human marking real performance after publication.

Two classes of check:
  HARD  — truthfulness / legal gates. Any failure blocks the draft outright.
          These are the checks the self-improvement loop is FORBIDDEN to mutate.
  SOFT  — craft mechanics. Failures lower the score, the loop may tune them.

Usage
-----
  python3 scripts/craft_score.py drafts/2026-07-29-msp-gap.md
  python3 scripts/craft_score.py drafts/*.md --json
  python3 scripts/craft_score.py drafts/x.md --quiet   # exit code only

Exit codes: 0 = no HARD failure, 1 = HARD failure, 2 = bad usage.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Overridable so the calibration gate in tests/ can point at fixture doctrine
# instead of the live allowlist. Live paths are the defaults.
CLAIMS_FILE = Path(os.environ.get("ENGINE_CLAIMS", REPO / "doctrine" / "VERIFIED-CLAIMS.md"))
VOICE_FILE = Path(os.environ.get("ENGINE_VOICE", REPO / "doctrine" / "VOICE-PROFILE-founder.md"))
LEDGER = Path(os.environ.get("ENGINE_LEDGER", REPO / "engine.db"))
ARTIFACTS_FILE = Path(os.environ.get("ENGINE_ARTIFACTS", REPO / "doctrine" / "ARTIFACTS.md"))
DRAFTS_DIR = Path(os.environ.get("ENGINE_DRAFTS_DIR", REPO / "drafts"))

KEYWORD_COOLDOWN_DAYS = 14  # P-016: one unique CTA keyword, no reuse < 14d
HOOK_MAX_CHARS = 200        # LinkedIn desktop "see more" fold
WORDS_MIN, WORDS_MAX = 120, 300   # his median 137, longest ever 270
ARROWS_MIN, ARROWS_MAX = 4, 6   # VOICE-DNA:189 — reader bounces at arrow 7
EMOJI_MAX = 3            # 5 of his 8 posts have zero emoji
NAME_CEILING = 3            # B-005: 5+ named brands turns the anchor into spectacle
SKELETON_MATCH_ARROWS = 3   # B-007: 3+ identical arrow lines = same skeleton

# Cadence fingerprints belonging to the operator whose engine this was ported
# from. Reusing them puts one person's voice in another founder's mouth, which is
# the failure mode the voice boundary exists to prevent. Not mutable, not tunable.
BORROWED_SIGNATURES = (
    "watching the wrong scoreboard",
    "capture the decision. assign the owner. close the loop.",
    "the part that broke my brain",
    "here's the actual angle",
    "i rebuilt your",
)

BANNED_VOCAB = (
    "synergy", "leverage", "unlock", "transformation", "journey",
    "cutting-edge", "cutting edge", "revolutioniz", "game-chang", "game chang",
    "seamless", "supercharge",
)

# Claims disproved by primary sources on 2026-07-29. These are not style problems,
# they are false statements, and they are the most checkable sentences in a post.
# Evidence: doctrine/GROUND-TRUTH.md section M.
DEAD_CLAIMS = {
    "answers and forgets": "M365 Copilot memory is on by default and persists until the user deletes it",
    "forgets it by friday": "same: Copilot memory ships on by default since 2026-03",
    "answers your question and forgets": "same, plus Copilot Cowork is GA for long-running multi-step work",
}

# Certification claims. The site publishes none of these, so any affirmative use is
# fabricated. Architecture (own-cloud) is sayable; certification is not.
CERT_RE = re.compile(r"\b(SOC ?2|HIPAA|ISO ?270\d\d|BAA|PHI|FINRA|GDPR compliant)\b", re.I)
CERT_NEGATED = re.compile(r"\b(never|not|no|without|ban|forbid|imply|cannot|can't)\b", re.I)

SALARY_RE = re.compile(r"\$\s?[\d,.]+\s*[KM]?\s*(?:/|\s+(?:a|per)\s+)(?:year|yr|annum)", re.I)

SCARCITY_MARKERS = (
    "small number", "handful", "few seats", "limited", "spots", "round fills",
    "only a few", "closing soon", "last seat", "seats left", "slots left",
    "spots left", "seats remaining", "round is small", "before it fills",
)

# A count or a deadline is a scarcity claim on its own, whatever words surround it.
# The calibration gate caught this: "only 3 pilot seats left and the round closes
# Friday" matched none of the marker phrases above and sailed through.
SEAT_COUNT_RE = re.compile(r"\b(?:only\s+|just\s+)?\d+\s+(?:more\s+)?(?:pilot\s+|open\s+)?(?:seats?|slots?|spots?|places?)\b", re.I)
DEADLINE_RE = re.compile(
    r"\b(?:closes?|closing|ends?|ending|expires?|deadline|cut ?off)\b[^.\n]{0,20}"
    r"\b(?:on\s+)?(?:mon|tue|wed|thu|fri|sat|sun|today|tomorrow|tonight|midnight|"
    r"this week|next week|friday|monday|\d{1,2}(?:st|nd|rd|th)?)\b", re.I)

OWN_CLOUD_MARKERS = ("own aws", "own azure", "never leaves", "your own cloud", "our own aws")

# Third-party products Northwind's copy might name. Naming one is an INTEGRATION or
# COMPETITOR claim, not a customer claim, so it lands in the soft C-INTEGRATION
# check: it needs a tick in VERIFIED-CLAIMS before shipping, but it does not read
# as a fabricated customer, so it does not hard-block a work-in-progress draft.
VENDORS = {
    "Teams", "Notion", "Gmail", "Salesforce", "Airtable", "Confluence", "M365",
    "Microsoft", "Copilot", "AWS", "Azure", "Slack", "Jira", "HubSpot", "Asana",
    "SharePoint", "Outlook", "Zoom", "Anthropic", "Opus", "Claude", "OpenAI",
    "ChatGPT", "Webflow", "Google", "Workspace", "Office",
}

# Job titles and role words. Northwind's whole arrow list is built from these, and a
# role is not a company, so they never count as an entity claim.
ROLE_WORDS = {
    "Ops", "Manager", "Chief", "Staff", "COO", "CEO", "CFO", "CTO", "HR", "QBR",
    "MSP", "MSPs", "IT", "People", "Business", "Partner", "Director", "Client",
    "Lead", "Analyst", "Controller", "Bookkeeper", "Admin",
}

# Ordinary English words that get capitalised mid-sentence by line breaks,
# emphasis, or the arrow-list imperative voice ("→ Chase the follow up...").
COMMON_CAPS = {
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December", "AI", "US", "PS", "DM", "DMs",
    "I", "We", "They", "The", "A", "An", "It", "If", "Here", "Every", "First",
    "Then", "That", "What", "Want", "Most", "Nothing", "Capture", "Assign",
    "Close", "Comment", "Connect", "Like", "Repost", "Reposters", "So", "My",
    "But", "And", "Not", "No", "Yes", "Your", "You", "Our", "Their", "This",
    "These", "Those", "There", "When", "While", "Because", "Before", "After",
    "Since", "Now", "Answer", "Chase", "Flag", "Run", "Surface", "Boring",
    "Three", "Two", "One", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Is", "Was", "Are", "Were", "Northwind", "Northwind's",
}

ENTITY_SAFE = VENDORS | ROLE_WORDS | COMMON_CAPS

# Prefixes that make a token line-initial in practice, so it is sentence case,
# not a proper noun: arrow bullets, list markers, numbered CTA steps.
LINE_PREFIX = re.compile(r"^\s*(?:[→•\-*]|\d+[.)]|[0-9]️?⃣|\U0001F51F)\s*")


# ---------------------------------------------------------------------------
# Client config overlay
#
# Everything above is the engine default, measured for one account. A different
# account has a different voice, a different incumbent and a different set of
# disproved claims, so those values live in doctrine/config.json rather than in
# this file. The engine is the gate; the config is whose gate it is.
#
# Three deliberate properties:
#   1. Only the keys listed in CONFIG_KEYS are overridable. An unknown key is a
#      hard error, not a silent no-op, so a typo can never quietly disable a gate.
#   2. A malformed config is a hard error too. A config that fails to parse must
#      never fall through to "no restrictions".
#   3. No key here can turn a HARD check into a SOFT one. The classes are fixed
#      in code. Config tunes thresholds and word lists, never severity.
# ---------------------------------------------------------------------------
CONFIG_FILE = Path(os.environ.get("ENGINE_CONFIG", REPO / "doctrine" / "config.json"))

CONFIG_KEYS = {
    "keyword_cooldown_days": ("KEYWORD_COOLDOWN_DAYS", int),
    "hook_max_chars": ("HOOK_MAX_CHARS", int),
    "words_min": ("WORDS_MIN", int),
    "words_max": ("WORDS_MAX", int),
    "arrows_min": ("ARROWS_MIN", int),
    "arrows_max": ("ARROWS_MAX", int),
    "emoji_max": ("EMOJI_MAX", int),
    "name_ceiling": ("NAME_CEILING", int),
    "skeleton_match_arrows": ("SKELETON_MATCH_ARROWS", int),
    "borrowed_signatures": ("BORROWED_SIGNATURES", tuple),
    "banned_vocab": ("BANNED_VOCAB", tuple),
    "dead_claims": ("DEAD_CLAIMS", dict),
    "scarcity_markers": ("SCARCITY_MARKERS", tuple),
    "own_cloud_markers": ("OWN_CLOUD_MARKERS", tuple),
    "vendors": ("VENDORS", set),
    "role_words": ("ROLE_WORDS", set),
    "common_caps": ("COMMON_CAPS", set),
}


def apply_config() -> str:
    """Overlay doctrine/config.json onto the engine defaults. Returns a label."""
    if not CONFIG_FILE.exists():
        return "engine defaults (no doctrine/config.json)"
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        sys.exit(f"config error: {CONFIG_FILE} is unreadable or invalid JSON ({exc}). "
                 "Refusing to score, because an unparsed config would silently relax every gate.")
    if not isinstance(cfg, dict):
        sys.exit(f"config error: {CONFIG_FILE} must contain a JSON object.")

    label = cfg.pop("_label", CONFIG_FILE.parent.parent.name)
    cfg.pop("_note", None)
    unknown = sorted(k for k in cfg if k not in CONFIG_KEYS)
    if unknown:
        sys.exit(f"config error: unknown key(s) in {CONFIG_FILE}: {', '.join(unknown)}. "
                 f"Known keys: {', '.join(sorted(CONFIG_KEYS))}.")

    g = globals()
    for key, value in cfg.items():
        name, kind = CONFIG_KEYS[key]
        if kind is int and not isinstance(value, int):
            sys.exit(f"config error: {key} must be an integer, got {value!r}.")
        if kind is dict and not isinstance(value, dict):
            sys.exit(f"config error: {key} must be an object, got {value!r}.")
        if kind in (tuple, set) and not isinstance(value, list):
            sys.exit(f"config error: {key} must be a list, got {value!r}.")
        g[name] = value if kind is int else kind(value)

    # Recompile the derived set, otherwise a config that adds role words or
    # vendors would be ignored by C-ENTITY, which is the strictest gate here.
    g["ENTITY_SAFE"] = set(VENDORS) | set(ROLE_WORDS) | set(COMMON_CAPS)
    return str(label)


CONFIG_LABEL = apply_config()


@dataclass
class Check:
    id: str
    name: str
    klass: str  # HARD | SOFT
    passed: bool
    detail: str


def strip_fences(text: str) -> str:
    """Drop fenced code blocks.

    Both doctrine files document their own line format inside a fence. Parsing
    those examples as live entries would silently allowlist the very figures the
    files exist to withhold ($30, Team FYM, pilot_seats: 8). The format block is
    documentation, not data.
    """
    return re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)


def load_claims() -> dict:
    """Parse doctrine/VERIFIED-CLAIMS.md — the allowlist that makes claims sayable.

    Recognised lines (anywhere in the file):
      money: $30 a seat a month | https://source | 2026-07-29
      entity: Team FYM | signed off by founder 2026-07-29
      pilot_seats: 8
    """
    claims = {"money": set(), "entity": set(), "pilot_seats": None, "scarcity": set()}
    if not CLAIMS_FILE.exists():
        return claims
    for line in strip_fences(CLAIMS_FILE.read_text(encoding="utf-8")).splitlines():
        line = line.strip().lstrip("-").strip()
        if line.lower().startswith("money:"):
            val = line.split(":", 1)[1].split("|")[0].strip()
            for fig in re.findall(r"\$[\d,.]+\s*[KMB]?", val):
                claims["money"].add(normalise_money(fig))
        elif line.lower().startswith("entity:"):
            claims["entity"].add(line.split(":", 1)[1].split("|")[0].strip())
        elif line.lower().startswith("scarcity_phrase:"):
            claims["scarcity"].add(line.split(":", 1)[1].split("|")[0].strip().lower())
        elif line.lower().startswith("pilot_seats:"):
            raw = line.split(":", 1)[1].strip()
            claims["pilot_seats"] = raw if re.fullmatch(r"\d+", raw) else None
    return claims


def normalise_money(fig: str) -> str:
    return fig.replace(",", "").replace(" ", "").upper()


def split_draft(text: str) -> tuple[str, str]:
    """Return (frontmatter_comment, body). Frontmatter is an HTML comment block."""
    m = re.match(r"\s*<!--(.*?)-->\s*", text, re.S)
    if m:
        return m.group(1), text[m.end():]
    return "", text


def fm_value(fm: str, key: str) -> str | None:
    m = re.search(rf"^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", fm, re.M | re.I)
    return m.group(1).strip() if m else None


def keyword_recently_used(keyword: str) -> str | None:
    """Return the offending date if this CTA keyword was used inside the cooldown."""
    if not LEDGER.exists():
        return None
    cutoff = (date.today() - timedelta(days=KEYWORD_COOLDOWN_DAYS)).isoformat()
    try:
        con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT posted_at FROM drafts WHERE UPPER(keyword)=? AND posted_at >= ?"
            " ORDER BY posted_at DESC LIMIT 1",
            (keyword.upper(), cutoff),
        ).fetchall()
        con.close()
    except sqlite3.Error:
        return None
    return rows[0][0] if rows else None


def run_checks(path: Path, claims: dict) -> list[Check]:
    raw = path.read_text(encoding="utf-8")
    fm, body = split_draft(raw)
    lines = [ln for ln in body.splitlines()]
    stripped = [ln.strip() for ln in lines if ln.strip()]
    low = body.lower()
    words = len(body.split())
    out: list[Check] = []

    def add(cid, name, klass, passed, detail=""):
        out.append(Check(cid, name, klass, bool(passed), detail))

    # ---- HARD: truthfulness and legal gates. The optimiser may not touch these.
    money_found = {normalise_money(f) for f in re.findall(r"\$[\d,.]+\s*[KMB]?", body)}
    unverified_money = sorted(money_found - claims["money"])
    add("C-MONEY", "every $ figure is in VERIFIED-CLAIMS", "HARD",
        not unverified_money,
        "unverified: " + ", ".join(unverified_money) if unverified_money else "all figures sourced")

    # Entity scan. Two different risks, so two different checks.
    #   customer claim  = a Title Case phrase we cannot account for -> HARD block
    #   vendor claim    = a named third-party product -> SOFT, needs a tick
    kw_declared = (fm_value(fm, "keyword") or "").upper()
    allow = ENTITY_SAFE | set(claims["entity"]) | {kw_declared}
    customer_cand, vendor_cand = set(), set()

    for ln in stripped:
        body_ln = LINE_PREFIX.sub("", ln)
        # Scan sentence by sentence, so a phrase can never straddle a full stop
        # ("...by Friday. Northwind deploys..." is not a company called "Friday Northwind").
        for sent in re.split(r"(?<=[.!?])\s+", body_ln):
            sent = sent.strip()
            if not sent:
                continue
            toks = re.findall(r"\b[A-Z][A-Za-z0-9&']*\b", sent)
            first = toks[0] if toks else None
            # A Title Case run of 2+ words is the shape a real company name takes.
            for phrase in re.findall(r"\b[A-Z][a-zA-Z0-9&']+(?:\s+[A-Z][a-zA-Z0-9&']+)+\b", sent):
                parts = phrase.split()
                if phrase in allow or all(p in allow for p in parts):
                    continue
                # Drop a leading sentence-initial word: "Northwind deploys" is not a name.
                if parts[0] == first and len(parts) == 2 and parts[1] in allow:
                    continue
                if all(p in ROLE_WORDS or p in COMMON_CAPS for p in parts):
                    continue
                customer_cand.add(phrase)
            for t in toks:
                if t in VENDORS and t not in claims["entity"]:
                    vendor_cand.add(t)
                elif t.isupper() and len(t) > 2 and t not in allow and t != first:
                    # All-caps emphasis of an ordinary word ("my ops lead WAS the
                    # system") is a voice device, not an entity. Only flag caps
                    # that appear nowhere else in the draft in lower case.
                    if re.search(rf"\b{re.escape(t.lower())}\b", low):
                        continue
                    customer_cand.add(t)

    add("C-ENTITY", "no unsigned-off customer or company named", "HARD",
        not customer_cand,
        "needs founder sign-off: " + ", ".join(sorted(customer_cand)) if customer_cand
        else "no unaccounted entities")

    add("C-INTEGRATION", "third-party products named are ticked in VERIFIED-CLAIMS", "SOFT",
        not vendor_cand,
        "unticked: " + ", ".join(sorted(vendor_cand)) if vendor_cand else "all vendor claims ticked")

    # Scarcity is sayable in exactly the form the site publishes, or with a real
    # seat count. Anything richer than the source ("a small number of seats", "when
    # the round fills") is an invention layered on top of a sourced phrase.
    numeric_seats = bool(SEAT_COUNT_RE.search(body))
    deadline = bool(DEADLINE_RE.search(body))
    marker = any(m in low for m in SCARCITY_MARKERS)
    has_scarcity = marker or numeric_seats or deadline
    sourced_form = any(p in low for p in claims["scarcity"]) if claims["scarcity"] else False

    if not has_scarcity:
        ok, why = True, "no scarcity claim made"
    elif deadline:
        # No deadline is published anywhere. A date is always an invention.
        ok, why = False, "deadline claim; no deadline is published"
    elif numeric_seats:
        ok = bool(claims["pilot_seats"])
        why = "numeric seat count with no pilot_seats source" if not ok else "seat count sourced"
    else:
        ok = sourced_form
        why = "sourced phrasing" if ok else "scarcity wording exceeds the sourced phrase"
    add("C-SCARCITY", "scarcity claim matches a sourced phrase or a real seat count",
        "HARD", ok, why)

    # Match the STATUS line, not the word anywhere in the file. The profile is
    # allowed to discuss the word "UNVERIFIED" in prose without blocking itself.
    voice_ready = VOICE_FILE.exists() and not re.search(
        r"^#*\s*STATUS:\s*UNVERIFIED", VOICE_FILE.read_text(encoding="utf-8"), re.M | re.I)
    add("C-VOICE", "founder voice profile is filled in, not a placeholder", "HARD",
        voice_ready,
        "VOICE-PROFILE-founder.md STATUS is still UNVERIFIED" if not voice_ready else "voice profile complete")

    persona = (fm_value(fm, "persona") or "").lower()
    first_person_receipt = bool(re.search(r"\b(we built|i am in the pilot|we let northwind|our own aws)\b", low))
    add("C-PERSONA", "first-person receipts match the declared posting account", "HARD",
        (not first_person_receipt) or persona in {"founder", "pilot-customer", "partner"},
        f"persona='{persona or 'MISSING'}' but draft makes first-person claims")

    # ---- SOFT: craft mechanics. The optimiser may tune wording around these.
    dash_hits = []
    for i, ln in enumerate(lines, 1):
        probe = re.sub(r"^\s*-\s", "", ln)  # allow a line-leading list marker
        if re.search(r"[—–]|--|\S-\S|\s-\s", probe):
            dash_hits.append(str(i))
    add("C-DASH", "no hyphens or em dashes in the body", "HARD",
        not dash_hits, "lines: " + ", ".join(dash_hits) if dash_hits else "clean")

    add("C-YT", "no YouTube links", "SOFT",
        "youtube.com" not in low and "youtu.be" not in low)

    hook = stripped[0] if stripped else ""
    add("C-HOOK", f"hook fits the fold (<= {HOOK_MAX_CHARS} chars)", "SOFT",
        0 < len(hook) <= HOOK_MAX_CHARS, f"{len(hook)} chars")

    # The arrow list is a ported device, not one the founder uses. Zero arrows is a
    # perfectly good post. Only the SHAPE of the list is scored, if there is one.
    arrows = [ln for ln in stripped if ln.startswith("→")]
    add("C-ARROWS", f"if arrows are used, {ARROWS_MIN}-{ARROWS_MAX} of them", "SOFT",
        (not arrows) or ARROWS_MIN <= len(arrows) <= ARROWS_MAX,
        f"{len(arrows)} arrows" if arrows else "no arrow list, fine")

    roled = [a for a in arrows if " like a" in a.lower() or " like an" in a.lower()]
    add("C-ARROW-ROLE", "every arrow ties to a real human role", "SOFT",
        (not arrows) or len(roled) == len(arrows),
        f"{len(roled)}/{len(arrows)} arrows name a role" if arrows else "no arrow list")

    kw = fm_value(fm, "keyword")
    kw_ok = bool(kw and re.fullmatch(r"[A-Z]{3,12}", kw))
    kw_hits = body.count('"' + kw + '"') if kw else 0
    add("C-KEYWORD", "one unique uppercase CTA keyword, quoted once in body", "SOFT",
        bool(kw_ok and kw_hits == 1),
        "keyword=" + repr(kw) + " quoted_occurrences=" + str(kw_hits))

    clash = keyword_recently_used(kw) if kw_ok else None
    add("C-KEYWORD-FRESH", f"CTA keyword unused in last {KEYWORD_COOLDOWN_DAYS} days", "SOFT",
        clash is None, f"reused, last seen {clash}" if clash else "fresh")

    # Measured: he closes with ONE plain-prose DM or comment ask, almost without
    # exception. The 4-step numbered emoji ladder is the ported house pattern and
    # appears nowhere in his 8 sampled posts, so it is now a violation, not a rule.
    ladder = sum(1 for e in ("1️⃣", "2️⃣", "3️⃣", "4️⃣") if e in body)
    add("C-NO-LADDER", "no ported numbered-emoji CTA ladder", "SOFT",
        ladder < 2, f"{ladder} ladder steps found; his close is one plain line")

    plain_close = bool(re.search(r"\b(dm me|comment below|drop a|comment or dm|dm or comment)\b", low))
    add("C-CLOSE", "closes with a plain prose DM or comment ask", "SOFT",
        plain_close, "no plain DM/comment close found")

    add("C-WORDS", f"body is {WORDS_MIN}-{WORDS_MAX} words", "SOFT",
        WORDS_MIN <= words <= WORDS_MAX, f"{words} words")

    add("C-OWNCLOUD", "own cloud / data residency beat present", "SOFT",
        any(m in low for m in OWN_CLOUD_MARKERS))

    emoji = len(re.findall(r"[\U0001F000-\U0001FAFF☀-➿♻❤]", body))
    add("C-EMOJI", f"emoji count <= {EMOJI_MAX}", "SOFT", emoji <= EMOJI_MAX, f"{emoji} emoji")

    pain = fm_value(fm, "pain")
    shape = fm_value(fm, "shape")
    add("C-DIALS", "pain and shape dials both declared in frontmatter", "SOFT",
        bool(pain and shape), f"pain={pain!r} shape={shape!r}")

    # ---- HARD: B-007 skeleton reuse. The feed habituates to the SHAPE, not the
    # topic. Measured collapse on the source engine when one skeleton was rerun
    # with a fresh logo each time: 48,919 -> 22,417 -> 10,864 -> 1,743.
    twin, shared = skeleton_twin(path, arrows)
    add("C-SKELETON", "arrow block is not a rerun of another draft's skeleton", "HARD",
        twin is None,
        f"shares {shared} arrow lines with {twin}" if twin else "skeleton is unique")

    # ---- HARD: voice theft. Cadence fingerprints from the source operator.
    dead = [f"{k} ({why})" for k, why in DEAD_CLAIMS.items() if k in low]
    add("C-DEADCLAIM", "no claim disproved by primary sources", "HARD",
        not dead, "; ".join(dead) if dead else "no disproved claims")

    cert_hits = [ln.strip() for ln in stripped
                 if CERT_RE.search(ln) and not CERT_NEGATED.search(ln)]
    add("C-CERT", "no certification claim (architecture is not certification)", "HARD",
        not cert_hits, "; ".join(h[:60] for h in cert_hits) if cert_hits else "no cert claims")

    borrowed = [s for s in BORROWED_SIGNATURES if s in low]
    add("C-BORROWED", "no borrowed cadence signatures from the source engine", "HARD",
        not borrowed, "borrowed: " + "; ".join(borrowed) if borrowed else "no borrowed signatures")

    # ---- HARD: the CTA may not promise an artifact that does not exist.
    promises_artifact = bool(re.search(r"\b(one page|map|playbook|checklist|template|guide)\b", low))
    add("C-ARTIFACT", "artifact promised in the CTA is listed live in ARTIFACTS.md", "HARD",
        (not promises_artifact) or artifact_is_live(),
        "CTA promises an artifact; none marked live in doctrine/ARTIFACTS.md"
        if promises_artifact else "no artifact promised")

    # ---- SOFT: B-005 name ceiling. Northwind's temptation is the 7-vendor integration list.
    named = {t for t in re.findall(r"\b[A-Z][A-Za-z0-9&']*\b", body) if t in VENDORS}
    add("C-NAMECOUNT", f"at most {NAME_CEILING} named brands in the body", "SOFT",
        len(named) <= NAME_CEILING, f"{len(named)} named: " + ", ".join(sorted(named)))

    salary_lines = SALARY_RE.findall(body)
    add("C-SALARY", "cost ladder is exactly 3 lines, or absent", "SOFT",
        len(salary_lines) in (0, 3), f"{len(salary_lines)} salary lines")

    banned = [w for w in BANNED_VOCAB if w in low]
    add("C-VOCAB", "no banned consultant vocabulary", "SOFT",
        not banned, "found: " + ", ".join(banned) if banned else "clean")

    return out


def skeleton_twin(path: Path, arrows: list[str]) -> tuple[str | None, int]:
    """B-007 gate: does another draft in drafts/ reuse this arrow block?"""
    if len(arrows) < SKELETON_MATCH_ARROWS:
        return None, 0
    mine = {re.sub(r"\s+", " ", a.lower().strip()) for a in arrows}
    best, best_n = None, 0
    for other in sorted(DRAFTS_DIR.glob("*.md")):
        if other.resolve() == path.resolve():
            continue
        try:
            _, other_body = split_draft(other.read_text(encoding="utf-8"))
        except OSError:
            continue
        theirs = {
            re.sub(r"\s+", " ", ln.strip().lower())
            for ln in other_body.splitlines() if ln.strip().startswith("→")
        }
        n = len(mine & theirs)
        if n > best_n:
            best, best_n = other.name, n
    return (best, best_n) if best_n >= SKELETON_MATCH_ARROWS else (None, best_n)


def artifact_is_live() -> bool:
    """True only if doctrine/ARTIFACTS.md marks at least one artifact live."""
    f = ARTIFACTS_FILE
    if not f.exists():
        return False
    body = strip_fences(f.read_text(encoding="utf-8"))
    return bool(re.search(r"^\s*-?\s*status:\s*live\b", body, re.M | re.I))


def report(path: Path, checks: list[Check], as_json: bool, quiet: bool) -> bool:
    hard_fails = [c for c in checks if c.klass == "HARD" and not c.passed]
    soft_fails = [c for c in checks if c.klass == "SOFT" and not c.passed]
    passed = sum(1 for c in checks if c.passed)

    if as_json:
        print(json.dumps({
            "file": str(path),
            "score": f"{passed}/{len(checks)}",
            "pass_rate": round(passed / len(checks), 3),
            "hard_fail": bool(hard_fails),
            "checks": [asdict(c) for c in checks],
        }, indent=2))
    elif not quiet:
        verdict = "BLOCKED" if hard_fails else ("PASS" if not soft_fails else "PASS with craft misses")
        print(f"\n{path.name}  {passed}/{len(checks)}  {verdict}")
        for c in checks:
            if not c.passed:
                mark = "HARD" if c.klass == "HARD" else "soft"
                print(f"  [{mark}] {c.id:<16} {c.name}" + (f"  ({c.detail})" if c.detail else ""))
        if not hard_fails and not soft_fails:
            print("  all checks clean")

    return not hard_fails


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    claims = load_claims()
    ok = True
    for f in args.files:
        if not f.exists():
            print(f"missing: {f}", file=sys.stderr)
            return 2
        ok = report(f, run_checks(f, claims), args.as_json, args.quiet) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
