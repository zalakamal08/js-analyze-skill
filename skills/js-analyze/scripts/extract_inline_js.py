#!/usr/bin/env python3
"""Extract inline <script> bodies from a list of HTML page URLs.

Inline JS is attack surface that bundle-only collection misses.
Run isolated:  python3 -I extract_inline_js.py --urls pages.txt --out inline/
Stdlib only. Fetches are plain GET; use browser-driven collection upstream if the
target blocks the default user-agent.
"""
import argparse, os, re, sys, urllib.request
from html.parser import HTMLParser

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class ScriptCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_script = False
        self.external = False
        self.buf = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            a = dict(attrs)
            self.external = "src" in a            # external handled elsewhere
            self.in_script = not self.external
            self.buf = []

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.in_script:
            body = "".join(self.buf).strip()
            if body:
                self.blocks.append(body)
        self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.buf.append(data)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        ct = r.headers.get_content_charset() or "utf-8"
        return r.read().decode(ct, "replace")


def safe_name(url):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", url)[:150]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", required=True, help="file with one HTML URL per line")
    ap.add_argument("--out", required=True, help="output dir for inline JS")
    args = ap.parse_args()
    if not os.path.isfile(args.urls):
        print(f"[extract_inline_js] url list not found: {args.urls} "
              "(did the crawl produce html_pages.txt?)", file=sys.stderr)
        return
    os.makedirs(args.out, exist_ok=True)

    total = 0
    with open(args.urls) as fh:
        urls = [l.strip() for l in fh if l.strip()]
    for url in urls:
        try:
            html = fetch(url)
        except Exception as e:  # noqa: BLE001 - best-effort recon fetch
            print(f"skip {url}: {e}", file=sys.stderr)
            continue
        p = ScriptCollector()
        p.feed(html)
        for i, block in enumerate(p.blocks):
            out = os.path.join(args.out, f"{safe_name(url)}__inline{i}.js")
            with open(out, "w") as o:
                o.write(block)
            total += 1
    print(f"extracted {total} inline blocks -> {args.out}")


if __name__ == "__main__":
    main()
