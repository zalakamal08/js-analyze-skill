#!/usr/bin/env python3
"""Hunt secrets in collected JS: known-regex matches + high-entropy strings.

Reports file:line + redacted context. Does NOT validate or use any secret.
Run isolated:  python3 -I find_secrets.py --indir beautified --maps maps --out secrets.md
Stdlib only.
"""
import argparse, math, os, re

KNOWN = {
    "AWS Access Key ID": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Google API Key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "Slack Token": re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),
    "Stripe Secret Key": re.compile(r"sk_live_[0-9A-Za-z]{24,}"),
    "GitHub Token": re.compile(r"gh[pousr]_[0-9A-Za-z]{36,}"),
    "JWT": re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    "Private Key Block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "Generic Assigned Secret": re.compile(
        r"(?i)(api[_-]?key|secret|token|passwd|password|auth)[\"'\s:=]+([0-9A-Za-z_\-./+]{12,})"),
}
# candidate high-entropy tokens
TOKEN = re.compile(r"[0-9A-Za-z_\-./+]{20,}")
ENTROPY_THRESHOLD = 4.0


def shannon(s):
    if not s:
        return 0.0
    freq = {c: s.count(c) for c in set(s)}
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def redact(s):
    s = s.strip()
    return s if len(s) <= 10 else f"{s[:4]}…{s[-4:]} ({len(s)} chars)"


def iter_files(*dirs):
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        for root, _x, files in os.walk(d):
            for name in files:
                if name.lower().endswith((".js", ".ts", ".map")):
                    yield os.path.join(root, name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", required=True)
    ap.add_argument("--maps", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    known_hits, entropy_hits = [], []
    for path in iter_files(args.indir, args.maps):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        for ln, line in enumerate(lines, 1):
            for label, rx in KNOWN.items():
                for m in rx.finditer(line):
                    val = m.group(len(m.groups())) if m.groups() else m.group(0)
                    known_hits.append((label, path, ln, redact(val)))
            for m in TOKEN.finditer(line):
                tok = m.group(0)
                if shannon(tok) >= ENTROPY_THRESHOLD and not any(
                        tok in h[3] for h in known_hits[-5:]):
                    entropy_hits.append((path, ln, round(shannon(tok), 2), redact(tok)))

    with open(args.out, "w") as o:
        o.write("# Secrets (redacted — values live only in OUTDIR)\n\n")
        o.write("## 5.1 Known-regex matches\n\n")
        o.write("| type | file:line | context |\n|---|---|---|\n")
        for label, path, ln, ctx in known_hits:
            o.write(f"| {label} | {path}:{ln} | `{ctx}` |\n")
        o.write(f"\n_{len(known_hits)} known matches._\n\n")
        o.write("## 5.2 High-entropy strings (no known pattern)\n\n")
        o.write("| file:line | entropy | context |\n|---|---|---|\n")
        # cap to keep the report readable; full set stays in tooling if needed
        for path, ln, ent, ctx in entropy_hits[:500]:
            o.write(f"| {path}:{ln} | {ent} | `{ctx}` |\n")
        o.write(f"\n_{len(entropy_hits)} high-entropy candidates (showing up to 500)._\n")
    print(f"known={len(known_hits)} entropy={len(entropy_hits)} -> {args.out}")


if __name__ == "__main__":
    main()
