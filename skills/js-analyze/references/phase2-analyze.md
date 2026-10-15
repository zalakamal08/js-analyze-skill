# Phase 2 — Analyze

Input: the normalized corpus from Phase 1 (`beautified/`, `maps/`, `raw/js_all.txt`).
Goal: turn raw JS into a structured map of the application's surface. Prefer AST-based
tools over raw regex where possible; fall back to regex for breadth.

Write every output under `$OUTDIR/reports/`. Keep a running note of file:line
provenance for each finding — the report requires it.

## 2.1 Endpoints

Extract URLs/paths referenced anywhere in the corpus. Resolve relative paths against
known `BASE_URL`/API-base constants found in the bundles. Use AST + regex extractors
together for coverage (exact syntax in `references/tools.md`).

```bash
# Primary — AST-aware
jsluice urls "$OUTDIR"/beautified/*.js > "$OUTDIR/reports/endpoints_raw.json"
# Complementary — regex (catches what AST misses)
xnLinkFinder -i "$OUTDIR/beautified" -sf "$SLUG" -o "$OUTDIR/reports/xnlinks.txt"
# Fallback if neither installed: grep the beautified corpus for URL/path literals.
```

Tag each endpoint: `live` (seen on the running site), `historical` (from Wayback),
`unauthed-guess` (reachable without auth — mark for manual confirmation only).
Output deduped `reports/endpoints.txt`.

## 2.2 Parameters → functions

Extract parameter names and, where the AST allows, the function/handler that consumes
each one. A parameter is far more useful tied to its calling function.

```bash
jsluice query "$OUTDIR"/beautified/*.js 2>/dev/null > "$OUTDIR/reports/params.json"
```

Record `param, function, file:line` rows.

## 2.3 API routes grouped by functionality

Cluster discovered calls into recognizable groups (e.g. `auth`, `user`, `billing`,
`admin`). Explicitly flag **old / unlinked versions** (`/api/v1/...` still answering
while `v3` is current) — these are high-value.

Output `reports/apis.md` with one section per group and a column for version status.

## 2.4 Secrets (two passes, kept separate)

Run the standard scanners first, then the stdlib fallback for breadth:

```bash
# Primary — TruffleHog over beautified + reconstructed sources (logs to stderr).
# No verified-only filter: on client data do NOT auto-verify secrets.
trufflehog filesystem "$OUTDIR/beautified" "$OUTDIR/maps" \
  --json 2>/dev/null > "$OUTDIR/reports/trufflehog.json"

# Secondary — gitleaks regex ruleset (no-git mode)
gitleaks detect --source "$OUTDIR/beautified" --no-git \
  --report-format json --report-path "$OUTDIR/reports/gitleaks.json"

# Fallback (zero-dep) — known-regex + high-entropy, redacted output
python3 -I "$HOME/.claude/skills/js-analyze/scripts/find_secrets.py" \
  --indir "$OUTDIR/beautified" --maps "$OUTDIR/maps" \
  --out "$OUTDIR/reports/secrets.md"
```

Consolidate hits from all scanners into `reports/secrets.md`, de-duplicated, kept in
two groups: (1) **known-pattern** matches and (2) **high-entropy / unverified**.
Each hit must carry `file:line` + context. **Never test, verify-by-use, or submit a
secret** — report it only. Treat all values as sensitive: redact in the report, do not
echo full secrets into chat, and do not commit them anywhere.

## 2.5 Third-party libraries → CVEs

Use **retire.js** (ships a known-vulnerability DB → CVEs directly); fall back to the
stdlib version-inventory script if retire is unavailable.

```bash
# Primary — retire.js maps bundled libs to known CVEs (retire 6.x: no --js flag)
retire --jspath "$OUTDIR/beautified" --outputformat json \
  --outputpath "$OUTDIR/reports/retire.json"

# Fallback — version inventory only (map to CVEs manually afterward)
python3 -I "$HOME/.claude/skills/js-analyze/scripts/detect_libraries.py" \
  --indir "$OUTDIR/beautified" --out "$OUTDIR/reports/libraries.md"
```

For each outdated/vulnerable lib, note version, latest, and CVE IDs. Do not run
exploit code — this is inventory only.

## 2.6 Framework & tech

Determine the frontend framework (React/Vue/Angular/Svelte/etc.) and build tooling.
Note framework-specific issue classes worth manual review (e.g. known SSR/hydration
or template pitfalls for that framework). Output to `reports/tech.md`.

## 2.7 Interesting items

Scan beautified JS + reconstructed sources for:
- admin / privileged route strings and role guards
- feature flags
- developer comments (TODO/FIXME/HACK, internal URLs, credentials-in-comments)
- hidden or debug routes

Output `reports/interesting.md` with file:line.

## 2.8 Client-side sinks / gadgets

Inventory dangerous **sinks** (e.g. `innerHTML`, `document.write`, `eval`,
`dangerouslySetInnerHTML`, `location`-writes, `postMessage` handlers) and the
**sources** that feed them. This is a map for later manual review of client-side
issues — do **not** craft or fire payloads here.

```bash
# Primary — semgrep static rules (DOM-XSS / audit), static only, no payloads
semgrep --config p/javascript --config p/xss \
  --json -o "$OUTDIR/reports/semgrep.json" "$OUTDIR/beautified"

# Fallback — sink/source mapper (flags sinks with a user-controllable source nearby)
python3 -I "$HOME/.claude/skills/js-analyze/scripts/map_sinks.py" \
  --indir "$OUTDIR/beautified" --out "$OUTDIR/reports/sinks.md"
```

## 2.9 Build outputs

Assemble `reports/report.md` per `references/report-format.md`, and generate
`reports/curls.sh` — one reproducible, non-destructive `curl` (GET/HEAD or documented
method) per discovered call, so a developer or a follow-up step can replay them.
curl commands are for reproducibility of *discovered* calls only; they must not
include attack payloads.

## 2.10 Review gate

Run `references/review.md` (Phase-2 section). It verifies each checklist item produced
a non-empty artifact with provenance, and that secrets/sinks are reported (not acted
on). Fix gaps, then mark the skill complete.
