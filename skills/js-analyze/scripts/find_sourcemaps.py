#!/usr/bin/env python3
"""Probe JS URLs for leaked source maps and reconstruct original sources.

For each JS URL: try <url>.map, read a trailing //# sourceMappingURL= comment, and
resolve relative map refs. If a map is found, write each original source file from the
map's sourcesContent into out/<host>/<path>.

Run isolated:  python3 -I find_sourcemaps.py --infile js_all.txt --out maps/
Stdlib only.
"""
import argparse, json, os, re, sys, urllib.parse, urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
SMRE = re.compile(rb"//[#@]\s*sourceMappingURL=([^\s'\"]+)")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def try_map_urls(js_url, body):
    """Yield candidate source-map URLs for a given JS url/body."""
    yield js_url + ".map"
    m = SMRE.search(body or b"")
    if m:
        ref = m.group(1).decode("utf-8", "replace")
        if ref.startswith("data:"):
            return
        yield urllib.parse.urljoin(js_url, ref)


def write_sources(mapdata, outdir):
    sources = mapdata.get("sources") or []
    contents = mapdata.get("sourcesContent") or []
    n = 0
    for i, src in enumerate(sources):
        if i >= len(contents) or contents[i] is None:
            continue
        rel = re.sub(r"^(\.\./|/|webpack://|\w+://)+", "", src)
        rel = re.sub(r"[^A-Za-z0-9._/-]+", "_", rel) or f"src{i}.js"
        dest = os.path.join(outdir, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w") as o:
            o.write(contents[i])
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", required=True, help="file of JS URLs, one per line")
    ap.add_argument("--out", required=True, help="output dir for reconstructed sources")
    args = ap.parse_args()
    if not os.path.isfile(args.infile):
        print(f"[find_sourcemaps] JS url list not found: {args.infile} "
              "(expected raw/js_all.txt from the merge step)", file=sys.stderr)
        return
    os.makedirs(args.out, exist_ok=True)

    found = recon = 0
    with open(args.infile) as fh:
        urls = [l.strip() for l in fh if l.strip()]
    for js in urls:
        try:
            body = fetch(js)
        except Exception:  # noqa: BLE001
            body = b""
        for cand in try_map_urls(js, body):
            try:
                raw = fetch(cand)
                data = json.loads(raw.decode("utf-8", "replace"))
            except Exception:  # noqa: BLE001
                continue
            host = urllib.parse.urlparse(js).netloc or "unknown"
            n = write_sources(data, os.path.join(args.out, host))
            if n:
                found += 1
                recon += n
                print(f"[map] {cand} -> {n} sources", file=sys.stderr)
            break
    print(f"maps found: {found}, sources reconstructed: {recon} -> {args.out}")


if __name__ == "__main__":
    main()
