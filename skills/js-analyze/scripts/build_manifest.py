#!/usr/bin/env python3
"""Build a provenance manifest (url/path, sha256, bytes) for collected JS.

Run isolated:  python3 -I build_manifest.py --indir <raw> --out manifest.csv
Stdlib only.
"""
import argparse, csv, hashlib, os, sys


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indir", required=True, help="directory of collected files")
    ap.add_argument("--out", required=True, help="output CSV path")
    args = ap.parse_args()

    rows = []
    for root, _dirs, files in os.walk(args.indir):
        for name in files:
            if not name.lower().endswith((".js", ".pretty.js")):
                continue
            p = os.path.join(root, name)
            try:
                rows.append((p, sha256(p), os.path.getsize(p),
                             os.path.basename(root)))
            except OSError as e:
                print(f"skip {p}: {e}", file=sys.stderr)

    with open(args.out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["path", "sha256", "bytes", "source"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
