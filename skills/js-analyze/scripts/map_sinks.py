#!/usr/bin/env python3
"""Map client-side sinks (and nearby sources) in collected JS for manual review.

Mapping only: it records where dangerous sinks appear and whether a user-controlled
source appears on the same line/nearby. It generates NO payloads and tests nothing.
Run isolated:  python3 -I map_sinks.py --indir beautified --out sinks.md
Stdlib only.
"""
import argparse, os, re

SINKS = {
    "innerHTML": re.compile(r"\.innerHTML\s*="),
    "outerHTML": re.compile(r"\.outerHTML\s*="),
    "document.write": re.compile(r"document\.write(?:ln)?\s*\("),
    "eval": re.compile(r"\beval\s*\("),
    "Function ctor": re.compile(r"\bnew\s+Function\s*\("),
    "setTimeout(str)": re.compile(r"setTimeout\s*\(\s*['\"]"),
    "dangerouslySetInnerHTML": re.compile(r"dangerouslySetInnerHTML"),
    "insertAdjacentHTML": re.compile(r"insertAdjacentHTML\s*\("),
    "location write": re.compile(r"(?:location\.(?:href|assign|replace)|window\.location)\s*="),
    "postMessage handler": re.compile(r"addEventListener\s*\(\s*['\"]message['\"]"),
    "jQuery html()": re.compile(r"\$\([^)]*\)\.html\s*\("),
}
SOURCES = re.compile(
    r"location\.(?:hash|search|href|pathname)|document\.(?:URL|referrer|cookie)"
    r"|window\.name|URLSearchParams|\.getParameter|event\.data|postMessage")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = []
    for root, _x, files in os.walk(args.indir):
        for name in files:
            if not name.lower().endswith((".js", ".ts")):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    lines = fh.readlines()
            except OSError:
                continue
            for ln, line in enumerate(lines, 1):
                for label, rx in SINKS.items():
                    if rx.search(line):
                        window = "".join(lines[max(0, ln - 3):ln + 2])
                        src = "yes" if SOURCES.search(window) else "—"
                        rows.append((label, src, f"{path}:{ln}"))

    with open(args.out, "w") as o:
        o.write("# Client-side sinks / gadgets (mapping only)\n\n")
        o.write("For manual review. No payloads generated. 'source nearby' = a "
                "user-controllable source appears within ~2 lines.\n\n")
        o.write("| sink | source nearby | file:line |\n|---|---|---|\n")
        for label, src, loc in rows:
            o.write(f"| {label} | {src} | {loc} |\n")
        o.write(f"\n_{len(rows)} sink occurrences._\n")
    print(f"sinks: {len(rows)} -> {args.out}")


if __name__ == "__main__":
    main()
