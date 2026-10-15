# Review gate

A second, adversarial pass run at the end of each phase to beat completion bias.
Do not accept "done" — verify each item actually produced output. If any check fails,
fix it and re-run this gate before advancing.

## How to run

For each checklist item in the phase, confirm: (a) the step ran, (b) it wrote a
non-empty artifact, (c) findings carry `file:line` provenance where applicable.
Record pass/fail per item in `$OUTDIR/progress.md`.

## Phase 1 checks

- [ ] `raw/js_live.txt` exists and is non-empty
- [ ] Inline JS was actually extracted (not just attempted) — `raw/inline/` populated
- [ ] Lazy/dynamic chunks resolved — chunk count sane vs. the runtime manifest
- [ ] `raw/js_historical.txt` present and merged into `raw/js_all.txt`
- [ ] JS actually **downloaded** to `raw/files/` (count ≈ non-empty lines of `js_all.txt`)
- [ ] Source-map probe ran for every entry in `js_all.txt`; found maps reconstructed
- [ ] All JS beautified into `beautified/`
- [ ] `raw/manifest.csv` has a row per collected file with sha256
- [ ] Count check: `wc -l raw/js_all.txt` ≥ number of live bundles observed in browser

Common misses to re-check explicitly: **inline JS**, **lazy-loaded chunks**,
**source maps on alternate domains/dirs**, **historical not merged**.

## Phase 2 checks

- [ ] `endpoints.txt` non-empty, each line tagged (live/historical/unauthed-guess)
- [ ] `params.json` maps params to functions where AST allowed
- [ ] `apis.md` groups calls and flags old/unlinked versions
- [ ] `secrets.md` has BOTH a known-regex section AND a high-entropy section, each hit
      with file:line + context; no secret values pasted into chat
- [ ] `libraries.md` lists versions + CVE IDs for outdated libs (inventory only)
- [ ] `tech.md` names the framework + review notes
- [ ] `interesting.md` includes comments/flags/admin routes with file:line
- [ ] `sinks.md` lists sinks and their sources (mapping only, no payloads)
- [ ] `report.md` and `curls.sh` exist; curls are non-destructive and payload-free

## Boundary check (every phase)

- [ ] All activity stayed within authorized scope hosts
- [ ] No secret was used/validated against any service
- [ ] No exploit payloads were generated or sent — this skill maps surface only
