# js-analyze — a JavaScript attack-surface recon skill

A systematic **Claude Code / Agent Skill** for authorized bug-bounty and penetration-
testing recon. It turns a web target's JavaScript into a structured map of its attack
surface — endpoints, parameters, API routes, secrets, vulnerable libraries, framework,
and client-side sinks — and produces a clean markdown report plus reproducible curl
commands.

> **Authorized use only.** This skill **maps attack surface; it does not exploit.**
> Run it only against targets you have written permission to test (bug-bounty scope
> or a signed engagement). Secrets found are reported, never used or validated.

---

## Credit & inspiration

The methodology encoded here is adapted from **Jason Haddix's** masterclass on building
hackbots, where he walks through designing a `js analyze` skill as the worked example:

- 🎥 **Hackbots | DEF CON 34 | BBV Masterclass with Jason Haddix**
  https://www.youtube.com/watch?v=cRKToFkZMvk
  (Bug Bounty Village — DEF CON 34)
- 🧑‍🏫 Speaker: **Jason Haddix** — [@Jhaddix](https://x.com/Jhaddix) · [arcanum-sec.com](https://arcanum-sec.com/)

All credit for the underlying approach (two-phase design, "completion bias" → small
discrete skills, the discover→analyze split, source-map/historical hunting, and the
design-question method) goes to Jason Haddix and the Arcanum team. This repository is
an independent, open implementation of that methodology as a reusable skill.

---

## What it does

Two **discrete phases** (the fix for "completion bias" — agents that do 3 of 20 steps
and report "done"), each with its own checklist and a mandatory review gate:

### Phase 1 — Discover & Download
- Crawl live site; collect **external bundles** + **inline JS** (commonly missed)
- Capture **lazy-loaded / dynamic chunks**
- Pull **historical** JS (Wayback / waymore) — incl. old `v1`/`v2` APIs not linked anywhere live
- Probe every file for leaked **source maps** and reconstruct original sources
- Merge, **download to disk**, deobfuscate/beautify, and build a provenance manifest

### Phase 2 — Analyze
- **Endpoints** (tagged live / historical / unauthed-guess)
- **Parameters** mapped to their consuming functions
- **API routes** grouped by functionality, flagging old/unlinked versions
- **Secrets** — known-pattern + high-entropy (reported, never used)
- **Third-party libraries** → known CVEs
- **Framework & tech** fingerprint + relevant issue classes
- **Client-side sinks/gadgets** mapped to their sources for manual review
- Outputs: `report.md`, `endpoints.txt`, `curls.sh`, `secrets.md`

---

## Tooling

Prefers industry-standard tools, with a **zero-dependency stdlib fallback** for every
job so the skill still runs on a bare box:

| Job | Primary | Fallback (included) |
|---|---|---|
| Secrets | TruffleHog, gitleaks | `scripts/find_secrets.py` |
| Vulnerable libs → CVEs | retire.js | `scripts/detect_libraries.py` |
| Endpoints / params | jsluice, LinkFinder/xnLinkFinder | source-map reconstruct + grep |
| Sinks / DOM | semgrep | `scripts/map_sinks.py` |
| Source maps | — | `scripts/find_sourcemaps.py` |
| Collection | katana, waymore, getJS, subjs, gau | — |

Install the primaries (no sudo):

```bash
bash skills/js-analyze/scripts/install_tools.sh
```

---

## Install the skill

Copy it into your Claude Code skills directory:

```bash
# personal (all projects)
cp -r skills/js-analyze ~/.claude/skills/

# or project-scoped
cp -r skills/js-analyze .claude/skills/
```

Then invoke it:

```
/js-analyze https://app.target-in-scope.com
```

See [`skills/js-analyze/SKILL.md`](skills/js-analyze/SKILL.md) for the full procedure,
and the [`references/`](skills/js-analyze/references) folder for the per-phase playbooks,
tool syntax, review gate, and report format.

---

## Layout

```
skills/js-analyze/
├── SKILL.md                 # orchestrator: phases, checklists, execution loop
├── references/
│   ├── phase1-discover.md    # collection pipeline
│   ├── phase2-analyze.md     # analysis pipeline
│   ├── tools.md              # exact command syntax, primary + fallback
│   ├── review.md             # per-phase review gate (anti completion-bias)
│   └── report-format.md      # fixed report skeleton
└── scripts/                 # stdlib-only fallbacks + tool installer
```

---

## License

MIT — see [LICENSE](LICENSE).

---

Built by [@zalakamal08](https://github.com/zalakamal08).
