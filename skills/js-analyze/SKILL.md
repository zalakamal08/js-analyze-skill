---
name: js-analyze
description: >-
  Map a web target's JavaScript attack surface for authorized bug bounty / pentest
  recon. Runs in two discrete phases: (1) DISCOVER & DOWNLOAD every piece of JS
  (inline, bundled, lazy-loaded, historical/Wayback, and leaked source maps),
  deobfuscate and store it; (2) ANALYZE the collected JS to extract endpoints,
  parameters mapped to functions, API routes (incl. old/unlinked versions), secrets
  (known-regex + high-entropy), third-party libraries and their known CVEs, the
  frontend framework, and dangerous client-side sinks/gadgets. Produces a markdown
  report plus reproducible curl commands. Use when asked to analyze JavaScript,
  map endpoints/APIs from JS, hunt JS secrets, or enumerate client-side attack
  surface for a target you are authorized to test.
arguments: [target]
argument-hint: "[target-base-url]"
---

# JS Analyze

Authorized-recon skill. Only run against targets the operator has written permission
to test (bug bounty scope or signed engagement). This skill **maps attack surface**;
it does not exploit.

## Why two phases

A single mega-methodology causes **completion bias**: the agent does 3 of 20 steps
and reports "done." This skill is therefore split into two sub-skills that run one
after the other, each with its own completion checklist and a mandatory review gate.

- **Phase 1 — Discover & Download** → `references/phase1-discover.md`
- **Phase 2 — Analyze** → `references/phase2-analyze.md`

Do **not** start Phase 2 until Phase 1's checklist is fully ticked and reviewed.

## Operating rules (read first)

1. **Scope gate.** Confirm the target host(s) are in authorized scope before any
   request. If scope is unclear, stop and ask.
2. **One task at a time.** Work the checklist top to bottom. After each item, write
   its status to `OUTDIR/progress.md`. Never skip an unchecked item silently.
3. **Full paths, full commands.** Every tool call uses absolute paths and complete
   commands (see `references/tools.md`, which lists exact syntax for every tool) —
   never just a tool name.
4. **Proper tools first, fallback second.** Prefer the industry-standard tool for
   each job (TruffleHog/gitleaks for secrets, retire.js for vulnerable libs, jsluice/
   LinkFinder for endpoints, semgrep for sinks, katana/waymore for collection). Each
   has a zero-dependency stdlib fallback in `scripts/` if the tool is missing. Run
   `scripts/install_tools.sh` once to install the primaries.
5. **Everything to disk.** All artifacts land under a single output folder so the
   work is resumable and auditable.
6. **Review gate.** At the end of each phase, invoke the review step in
   `references/review.md` and fix anything it flags before continuing.

## Execution loop (how to actually run this — defeats completion bias)

For each phase: `Read` the phase doc → do step N → run its exact command → write the
result + a ✓/✗ line to `OUTDIR/progress.md` → only then move to step N+1. Do **not**
batch steps or declare the phase done from memory. After the last step, run the review
gate; it re-checks every item produced a real, non-empty artifact. If anything is ✗,
fix it before the next phase. Phase 2 may not begin until Phase 1 is fully ✓ + reviewed.

## Setup

`$target` below is the argument passed to the skill. If it is empty (skill was
model-invoked without one), stop and ask the operator for the in-scope base URL.

```bash
TARGET="$target"
[ -z "$TARGET" ] && { echo "No target passed — ask the operator for the in-scope base URL"; exit 1; }
SLUG="$(echo "$TARGET" | sed -E 's~https?://~~; s~[^A-Za-z0-9.]+~_~g')"
OUTDIR="$HOME/recon/js-analyze/${SLUG}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTDIR"/{raw,beautified,maps,reports}
echo "OUTDIR=$OUTDIR"
```

One-time: install the preferred toolchain, then record which tools are available so the
agent knows when to use a fallback.

```bash
bash "$HOME/.claude/skills/js-analyze/scripts/install_tools.sh"   # first run only
{ echo "# tools"; for t in trufflehog gitleaks jsluice linkfinder retire getJS \
    subjs waymore mantra katana gau nuclei semgrep npx; do
    command -v "$t" >/dev/null 2>&1 && echo "ok   $t" || echo "MISS $t"; done; } \
  >> "$OUTDIR/progress.md"
```

Record `TARGET` and `OUTDIR` at the top of `OUTDIR/progress.md` and proceed to Phase 1.

## Phase 1 — Discover & Download  (checklist)

Full procedure: `references/phase1-discover.md`

- [ ] 1.1 Crawl live site; split output into **external .js bundles** + **HTML page list**
- [ ] 1.2 Capture **inline JS** embedded in HTML pages (commonly missed)
- [ ] 1.3 Capture **lazy-loaded / dynamically-imported** chunks
- [ ] 1.4 Pull **historical** JS URLs (Wayback / waymore) incl. v1/v2 APIs not linked anywhere live
- [ ] 1.5 **Merge** live+historical+chunks into `raw/js_all.txt` and **download** all JS to `raw/files/`
- [ ] 1.6 For every JS URL, probe for a leaked **source map** (`.map`, `//# sourceMappingURL`); reconstruct sources; also check sibling dirs and alternate domains
- [ ] 1.7 (Optional) If a mobile app exists, note it may ship the same JS + source maps
- [ ] 1.8 **Deobfuscate / beautify** downloaded + inline JS into `beautified/`
- [ ] 1.9 **Store** a manifest (`raw/manifest.csv`: path,sha256,bytes,source)
- [ ] 1.10 Run the Phase-1 review gate; fix gaps

➡️ Only when every box is checked: proceed to Phase 2.

## Phase 2 — Analyze  (checklist)

Full procedure: `references/phase2-analyze.md`

- [ ] 2.1 **Endpoints** — extract all, tagged: live | historical | unauthed-guess
- [ ] 2.2 **Parameters** — extract and map each to the function that uses it
- [ ] 2.3 **API routes** — group calls by functionality (user API, admin API, …); flag old/unlinked versions
- [ ] 2.4 **Secrets** — known-regex matches **and** high-entropy strings (separate lists, with context)
- [ ] 2.5 **Third-party libraries** — identify + versions → known CVEs
- [ ] 2.6 **Framework & tech** — frontend framework + known attack patterns for it
- [ ] 2.7 **Interesting items** — admin flags, feature flags, developer comments, hidden routes
- [ ] 2.8 **Client-side sinks/gadgets** — map dangerous functions (sinks) and sources for later review
- [ ] 2.9 **Build outputs** — markdown report + curl commands (see `references/report-format.md`)
- [ ] 2.10 Run the Phase-2 review gate; fix gaps

## Finished artifacts (definition of done)

- `reports/report.md` — the full findings report in the required format
- `reports/endpoints.txt` — deduped endpoint list with tags
- `reports/curls.sh` — one reproducible curl per discovered call
- `reports/secrets.md` — known + high-entropy, each with file:line and context
- `progress.md` — every checklist item marked done, with notes

A phase is not "done" until its checklist is fully ticked, the review gate passed,
and the artifacts above exist and are non-empty where applicable.
