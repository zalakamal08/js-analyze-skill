# Report format — reports/report.md

The report is the finished artifact. Use this exact skeleton so output is consistent
across runs and across targets.

```markdown
# JS Analysis — <TARGET>

- **Date:** <YYYY-MM-DD>
- **Scope:** <authorized host(s)>
- **Output dir:** <OUTDIR>
- **Corpus:** <N live> + <N historical> JS files, <N> source maps reconstructed

## 1. Summary
2–5 bullets: biggest surface items and anything needing manual follow-up.

## 2. Endpoints
Table: `endpoint | method(s) | tag (live/historical/unauthed-guess) | source file:line`

## 3. API routes (grouped)
Per functional group (auth/user/admin/…): the routes, with a **version status** column
flagging old/unlinked versions still answering.

## 4. Parameters → functions
Table: `param | consuming function | file:line`

## 5. Secrets
### 5.1 Known-regex matches
Table: `type | file:line | context (redacted value)`
### 5.2 High-entropy strings
Table: `file:line | entropy | context (redacted value)`
> Values redacted; full values remain only in OUTDIR, never in chat or VCS.

## 6. Third-party libraries
Table: `library | version | latest | known CVEs`

## 7. Framework & tech
Framework, build tooling, and framework-specific classes worth manual review.

## 8. Interesting items
Admin/feature flags, developer comments, hidden/debug routes — with file:line.

## 9. Client-side sinks / gadgets
Table: `sink | source feeding it | file:line` — mapping only, for manual review.

## 10. Reproduction
Reference `reports/curls.sh` (non-destructive, payload-free replays of discovered calls).

## 11. Coverage / gaps
What was and wasn't reachable; follow-ups (e.g. mobile app may ship same JS + maps).
```

Rules:
- Every finding cites `file:line`.
- Secrets are **redacted** in the report; never paste full values into chat.
- The report maps attack surface; it contains **no exploit payloads**.
