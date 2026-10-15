# Tools reference — exact syntax upfront

Give the agent **full commands, not just tool names.** Every command below is
copy-paste ready; substitute `$OUTDIR`/`$TARGET`/`$SLUG`. For each job there is a
**primary** (industry-standard) tool and a **fallback** (the skill's stdlib script,
zero external deps). Prefer the primary; fall back only if it is not installed.

First run `scripts/install_tools.sh` once to install the primaries (no sudo needed).

Installed-tool check (run at skill start, record in progress.md):
```bash
for t in trufflehog gitleaks jsluice linkfinder retire getJS subjs waymore \
         mantra katana gau nuclei semgrep npx; do
  command -v "$t" >/dev/null 2>&1 && echo "ok $t" || echo "MISS $t"
done
```

---

## Phase 1 — collection

### Crawl live site (JS + pages)
```bash
katana -u "$TARGET" -jc -d 3 -silent > "$OUTDIR/raw/all_urls.txt"
```
Fallbacks: `hakrawler -url "$TARGET" -js`, `gau --subs "$SLUG"`, `waybackurls`.

### Collect JS URLs specifically
```bash
getJS --url "$TARGET" --complete            # getJS
subjs -i "$OUTDIR/raw/hosts.txt"            # subjs (from a host list)
```

### Historical URLs (hidden/retired endpoints)
```bash
waymore -i "$SLUG" -mode U                  # URLs mode
gau --subs "$SLUG"                          # fallback
```

### Download JS locally
```bash
curl -sSL --max-time 30 -A "$UA" "$URL" -o "$OUTDIR/raw/files/<name>.js"
```
If blocked by bot protection, use **Playwright MCP** (browser-driven, below).

### Beautify / deobfuscate
```bash
npx --yes js-beautify "$f" > "$OUTDIR/beautified/$(basename "$f").pretty.js"
```

### Source maps → original sources
Primary: `scripts/find_sourcemaps.py` (probes `.map`, `sourceMappingURL`, reconstructs).
```bash
python3 -I "$HOME/.claude/skills/js-analyze/scripts/find_sourcemaps.py" \
  --infile "$OUTDIR/raw/js_all.txt" --out "$OUTDIR/maps"
```
Alt: `npx --yes sourcemapper -url "$URL.map" -output "$OUTDIR/maps/<host>"`.

---

## Phase 2 — analysis

### Endpoints / params (AST-aware)   ← primary
```bash
jsluice urls  "$OUTDIR"/beautified/*.js   > "$OUTDIR/reports/endpoints_raw.json"
jsluice query "$OUTDIR"/beautified/*.js   > "$OUTDIR/reports/params.json"
jsluice secrets "$OUTDIR"/beautified/*.js > "$OUTDIR/reports/jsluice_secrets.json"
```

### Endpoints (regex)   ← complementary
```bash
# xnLinkFinder (primary — scans a whole dir, finds links + params):
xnLinkFinder -i "$OUTDIR/beautified" -sf "$SLUG" -o "$OUTDIR/reports/xnlinks.txt"
# LinkFinder (optional alt, per file; install from git if you want it):
#   for f in "$OUTDIR"/beautified/*.js; do linkfinder -i "$f" -o cli; done \
#     | sort -u > "$OUTDIR/reports/linkfinder.txt"
```

### Secrets   ← TruffleHog primary (verified), then gitleaks, then fallback
```bash
# TruffleHog — filesystem mode over the whole corpus. Logs to stderr (redirect it);
# findings go to stdout as JSON. Do NOT filter to verified-only on client data.
trufflehog filesystem "$OUTDIR/beautified" "$OUTDIR/maps" \
  --json 2>/dev/null > "$OUTDIR/reports/trufflehog.json"

# gitleaks — fast regex ruleset, no-git mode on a directory
gitleaks detect --source "$OUTDIR/beautified" --no-git \
  --report-format json --report-path "$OUTDIR/reports/gitleaks.json"

# Fallback (zero-dep): known-regex + high-entropy
python3 -I "$HOME/.claude/skills/js-analyze/scripts/find_secrets.py" \
  --indir "$OUTDIR/beautified" --maps "$OUTDIR/maps" \
  --out "$OUTDIR/reports/secrets.md"
```
Report secrets only; never validate/use a value. `--only-verified` would send the
secret to the provider to confirm liveness — do NOT do that on client data; keep the
default (no auto-verification). Note: trufflehog/gitleaks allowlist well-known example
keys (e.g. the AWS `...EXAMPLE` key), so those won't show up — that's expected.
(`mantra` is an optional JS-secret grep; redundant with the above — skip if not installed.)

### Vulnerable third-party libraries → CVEs   ← retire.js primary
```bash
retire --jspath "$OUTDIR/beautified" --outputformat json \
  --outputpath "$OUTDIR/reports/retire.json"   # retire 6.x: no --js flag
# Fallback (version inventory only, no CVE DB):
python3 -I "$HOME/.claude/skills/js-analyze/scripts/detect_libraries.py" \
  --indir "$OUTDIR/beautified" --out "$OUTDIR/reports/libraries.md"
```

### Client-side sinks / DOM issues (mapping only)
```bash
# semgrep with DOM-XSS / audit rules (no payloads, static only):
semgrep --config p/javascript --config p/xss \
  --json -o "$OUTDIR/reports/semgrep.json" "$OUTDIR/beautified"
# Fallback: sink/source mapper
python3 -I "$HOME/.claude/skills/js-analyze/scripts/map_sinks.py" \
  --indir "$OUTDIR/beautified" --out "$OUTDIR/reports/sinks.md"
```

### Interesting params for later manual testing (classification only)
```bash
gf ssrf   "$OUTDIR"/beautified/*.js
gf redirect "$OUTDIR"/beautified/*.js
# gf only tags candidate patterns; it does NOT test anything.
```

---

## Browser-driven collection (when plain fetch is blocked)

Use **Playwright MCP** (`mcp__playwright__*`) for collection only — navigate in-scope
pages, let JS (incl. lazy chunks) load, then read captured requests:
- `mcp__playwright__browser_navigate` → the in-scope URL
- `mcp__playwright__browser_wait_for` → let chunks load / click routes
- `mcp__playwright__browser_network_requests` → filter `.js` → append to `js_live.txt`

Do not send crafted input via the browser — this skill maps surface only.

---

## Install matrix

| Job | Primary | Install | Fallback |
|---|---|---|---|
| Crawl | katana | `go install github.com/projectdiscovery/katana/cmd/katana@latest` | gau, hakrawler |
| JS URLs | getJS / subjs | `go install github.com/003random/getJS@latest` | grep on crawl |
| Historical | waymore | `pipx install waymore` | gau, waybackurls |
| Endpoints/params | jsluice | `go install github.com/BishopFox/jsluice/cmd/jsluice@latest` | LinkFinder; `find_sourcemaps`+grep |
| Links (regex) | xnLinkFinder | `pipx install xnLinkFinder` | LinkFinder (git install, optional) |
| Secrets | trufflehog | `install_tools.sh` | gitleaks; `find_secrets.py` |
| Vuln libs | retire.js | `npm i -g retire` | `detect_libraries.py` |
| Sinks | semgrep | `pipx install semgrep` | `map_sinks.py` |
| Param classes | gf | `go install github.com/tomnomnom/gf@latest` + patterns | — |

Isolation: run any script that reads downloaded (untrusted) JS with `python3 -I`, and
pass data paths as arguments only, so a planted module in the data dir can't be imported.
