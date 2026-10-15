# Phase 1 — Discover & Download

Goal: collect **every** piece of JavaScript the target serves — live, hidden, and
historical — plus any leaked source maps, download it all to disk, and normalize it.
Breadth here determines the ceiling of Phase 2.

Pipeline (producers → consumers):

```
crawl ─┬─> raw/js_live.txt ─┐
       └─> raw/html_pages.txt ──> inline JS ──> raw/inline/*.js
historical ─> raw/js_historical.txt ─┤
lazy chunks ──────────────> (appended to js_live.txt)
                              merge ──> raw/js_all.txt ──> download ──> raw/files/*.js
                                                        └─> source maps ──> maps/
beautify(raw/files + raw/inline) ──> beautified/*.js
manifest(raw/) ──> raw/manifest.csv
```

Work each step in order, write status to `$OUTDIR/progress.md`, store outputs under
`$OUTDIR`. Commands assume `TARGET`, `SLUG`, `OUTDIR` are exported (see SKILL.md Setup).
Export a browser-like UA once:

```bash
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
```

## 1.1 Crawl — live bundles + page list

Crawl the in-scope host once; split output into a JS list and an HTML-page list (the
page list feeds inline-JS extraction in 1.2).

```bash
katana -u "$TARGET" -jc -d 3 -silent > "$OUTDIR/raw/all_urls.txt"
grep -Ei '\.js(\?|$)'  "$OUTDIR/raw/all_urls.txt" | sort -u > "$OUTDIR/raw/js_live.txt"
grep -Eiv '\.(js|css|png|jpg|jpeg|gif|svg|woff2?|ico)(\?|$)' \
    "$OUTDIR/raw/all_urls.txt" | sort -u > "$OUTDIR/raw/html_pages.txt"
```

Fallbacks if katana is missing: `hakrawler`, `gau`, `waybackurls` (see tools.md).
If the live site blocks plain fetches, drive a real browser (tools.md →
"Browser-driven collection") and export its captured requests into these two files.

## 1.2 Inline JS (commonly missed)

Inline `<script>` blocks are attack surface too. Feed the page list from 1.1.

```bash
python3 -I "$HOME/.claude/skills/js-analyze/scripts/extract_inline_js.py" \
  --urls "$OUTDIR/raw/html_pages.txt" --out "$OUTDIR/raw/inline"
```

## 1.3 Lazy-loaded / dynamic chunks

Webpack/Vite split bundles load more chunks at runtime. Either parse the runtime/
manifest chunk for the chunk map and resolve chunk URLs, or load the page in a browser,
exercise routes, and capture newly-requested `.js`. Append any discovered chunk URLs:

```bash
# append resolved chunk URLs, then re-dedupe
sort -u -o "$OUTDIR/raw/js_live.txt" "$OUTDIR/raw/js_live.txt"
```

## 1.4 Historical JS (Wayback / waymore)

Retired endpoints — old `v1`/`v2` APIs kept alive but not linked anywhere — often
surface only in history.

```bash
waymore -i "$SLUG" -mode U \
  | grep -Ei '\.js(\?|$)' | sort -u > "$OUTDIR/raw/js_historical.txt"
```

## 1.5 Merge + download all JS to disk

Merge every source into one deduped list, then download each file locally (Phase 2's
analysis scripts read local files, not URLs).

```bash
cat "$OUTDIR/raw/js_live.txt" "$OUTDIR/raw/js_historical.txt" 2>/dev/null \
  | sort -u > "$OUTDIR/raw/js_all.txt"

mkdir -p "$OUTDIR/raw/files"
while IFS= read -r u; do
  [ -z "$u" ] && continue
  fn=$(printf '%s' "$u" | sed -E 's~https?://~~; s~[^A-Za-z0-9._-]+~_~g')
  curl -sSL --max-time 30 -A "$UA" "$u" -o "$OUTDIR/raw/files/${fn}.js"
done < "$OUTDIR/raw/js_all.txt"
```

If `curl` is blocked by bot protection, fetch via the browser engine instead (tools.md).

## 1.6 Source maps

For every JS URL, check for a map: a trailing `.map`, a `//# sourceMappingURL=`
comment, and common sibling locations. Reconstruct original sources.

```bash
python3 -I "$HOME/.claude/skills/js-analyze/scripts/find_sourcemaps.py" \
  --infile "$OUTDIR/raw/js_all.txt" --out "$OUTDIR/maps"
```

Also try neighboring directories and alternate domains (CDN, staging) for maps.

## 1.7 Mobile note (optional)

If the target ships a mobile app, it may bundle the same JS and even source maps.
Note it in `progress.md` as a follow-up source; do not pull APKs/IPAs unless in scope.

## 1.8 Deobfuscate / beautify

Normalize downloaded bundles and inline blocks so Phase 2 can read them. Use `find`
(not bash `**`, which needs `shopt -s globstar`).

```bash
mkdir -p "$OUTDIR/beautified"
find "$OUTDIR/raw/files" "$OUTDIR/raw/inline" -type f -name '*.js' 2>/dev/null |
while IFS= read -r f; do
  npx --yes js-beautify "$f" > "$OUTDIR/beautified/$(basename "$f").pretty.js" 2>/dev/null \
    || cp "$f" "$OUTDIR/beautified/$(basename "$f").pretty.js"
done
```

Map-reconstructed sources in `maps/` are already readable; analyze them in place.

## 1.9 Manifest

Provenance for everything collected under `raw/` (includes `files/` and `inline/`).

```bash
python3 -I "$HOME/.claude/skills/js-analyze/scripts/build_manifest.py" \
  --indir "$OUTDIR/raw" --out "$OUTDIR/raw/manifest.csv"
```

## 1.10 Review gate

Run `references/review.md` (Phase-1 section). Typical gaps it catches: inline JS not
captured, lazy chunks missed, nothing actually downloaded to `raw/files/`, no
source-map probe, historical not merged. Fix, then re-tick the checklist in SKILL.md.

## Consolidated inputs for Phase 2

- `raw/js_all.txt` — deduped URL list (live + historical + resolved chunks)
- `raw/files/*.js` — downloaded bundles; `raw/inline/*.js` — inline blocks
- `beautified/*.js` — readable JS (analysis target)
- `maps/` — reconstructed original sources (gold for analysis)
- `raw/manifest.csv` — provenance (path, sha256, bytes, source)
