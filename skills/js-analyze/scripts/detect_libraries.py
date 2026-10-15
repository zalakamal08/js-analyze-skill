#!/usr/bin/env python3
"""Inventory third-party JS libraries + versions from collected JS.

Inventory only — no CVE lookups are performed here (do that with a vuln DB / the
agent's knowledge afterward). Captures library name + version banners it can find.
Run isolated:  python3 -I detect_libraries.py --indir beautified --out libraries.md
Stdlib only.
"""
import argparse, os, re
from collections import defaultdict

# common version-banner patterns found in bundles/comments
PATTERNS = [
    re.compile(r"(?i)\b(react)\b[^0-9]{0,20}(\d+\.\d+\.\d+)"),
    re.compile(r"(?i)\b(angular)\b[^0-9]{0,20}(\d+\.\d+\.\d+)"),
    re.compile(r"(?i)\b(vue)\b[^0-9]{0,20}(\d+\.\d+\.\d+)"),
    re.compile(r"(?i)\b(jquery)\b[^0-9]{0,20}(\d+\.\d+\.\d+)"),
    re.compile(r"(?i)\b(lodash)\b[^0-9]{0,20}(\d+\.\d+\.\d+)"),
    re.compile(r"(?i)\b(moment)\b[^0-9]{0,20}(\d+\.\d+\.\d+)"),
    re.compile(r"(?i)\b(axios)\b[^0-9]{0,20}(\d+\.\d+\.\d+)"),
    re.compile(r"(?i)\b(bootstrap)\b[^0-9]{0,20}(\d+\.\d+\.\d+)"),
    re.compile(r"(?i)\b(d3)\b[^0-9]{0,20}(\d+\.\d+\.\d+)"),
    # generic "name@1.2.3" and "name v1.2.3"
    re.compile(r"\b([a-z][a-z0-9_.\-]{2,30})[@\s]v?(\d+\.\d+\.\d+)"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    found = defaultdict(set)  # (lib) -> {versions}
    where = defaultdict(set)  # (lib,ver) -> {file:line}
    for root, _x, files in os.walk(args.indir):
        for name in files:
            if not name.lower().endswith((".js", ".ts")):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    for ln, line in enumerate(fh, 1):
                        if ln > 50 and len(line) > 2000:
                            continue  # skip minified mega-lines for banner scan
                        for rx in PATTERNS:
                            for m in rx.finditer(line):
                                lib, ver = m.group(1).lower(), m.group(2)
                                found[lib].add(ver)
                                where[(lib, ver)].add(f"{path}:{ln}")
            except OSError:
                continue

    with open(args.out, "w") as o:
        o.write("# Third-party libraries (inventory)\n\n")
        o.write("Map each version to known CVEs afterward.\n\n")
        o.write("| library | version(s) | seen at (sample) |\n|---|---|---|\n")
        for lib in sorted(found):
            for ver in sorted(found[lib]):
                sample = sorted(where[(lib, ver)])[:2]
                o.write(f"| {lib} | {ver} | {'; '.join(sample)} |\n")
        o.write(f"\n_{sum(len(v) for v in found.values())} version records._\n")
    print(f"libraries: {len(found)} -> {args.out}")


if __name__ == "__main__":
    main()
