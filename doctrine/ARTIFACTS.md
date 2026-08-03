# ARTIFACTS.md — what a CTA is allowed to promise

`scripts/craft_score.py` reads this file. If a draft's CTA promises a map, a playbook,
a checklist, a template or a guide, at least one artifact here must be marked
`status: live` or the draft is a HARD failure.

The rule behind it: if there is nothing to deliver, kill the draft. A CTA that promises
an artifact which does not exist converts a warm reader into someone who thinks you
wasted their comment.

Format:

```
## <artifact name>
status: live | building | promised-not-built
url: <where it actually lives>
owner: <who is producing it>
proves: <the claim in the post it backs up>
```

---

Nothing is live yet. Until something is, the honest CTA is a plain ask with no
download attached.
