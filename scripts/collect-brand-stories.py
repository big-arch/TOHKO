"""Collect public catalogue evidence and optimise reviewed brand-story photographs.

No generated imagery. Each candidate retains the page URL and the exact image URL.
Run with --pages FILE (mapping of evidence names to URLs), or --photos FILE
(list with id, url and source). Network calls are read-only.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import html
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "qa" / "brand-stories16"
PILLOW = Path(r"C:\Users\Артур\Documents\CODEX_сайт_ТОНКО\.cache\pillow-runtime")
if PILLOW.exists():
    sys.path.insert(0, str(PILLOW))
sys.stdout.reconfigure(encoding="utf-8")


def get(url):
    # Windows curl uses the system certificate store; Python's trust store is
    # incomplete for several public catalogue hosts. Never disable TLS checks.
    result = subprocess.run(
        ["curl.exe", "--location", "--fail", "--silent", "--show-error",
         "--connect-timeout", "10", "--max-time", "30", "--user-agent", "Mozilla/5.0",
         "--write-out", "\nTONKO_EFFECTIVE_URL=%{url_effective}", url],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode == 0:
        data, final = result.stdout.rsplit(b"\nTONKO_EFFECTIVE_URL=", 1)
        return data, final.decode("utf-8"), "utf-8"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; TONKO catalogue research)"})
    try:
        res = urllib.request.urlopen(req, timeout=25)
    except urllib.error.URLError as exc:
        if "UNEXPECTED_EOF" not in str(exc):
            raise
        # Some catalogue hosts fail TLS 1.3; certificate verification remains on.
        context = ssl.create_default_context()
        context.maximum_version = ssl.TLSVersion.TLSv1_2
        res = urllib.request.urlopen(req, context=context, timeout=25)
    with res:
        return res.read(), res.geturl(), res.headers.get_content_charset() or "utf-8"


class Page(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base, self.images, self.links, self.text = base, [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("img", "source"):
            for key in ("src", "data-src", "data-original", "data-zoom-image", "srcset", "data-srcset"):
                if a.get(key):
                    for value in a[key].split(","):
                        value = value.strip().split(" ")[0]
                        if value and not value.startswith("data:"):
                            self.images.append({"url": urllib.parse.urljoin(self.base, value), "alt": a.get("alt", "")})
        if tag == "a" and a.get("href"):
            self.links.append({"url": urllib.parse.urljoin(self.base, a["href"])})

    def handle_data(self, data):
        s = data.strip()
        if s and len(s) < 5000:
            self.text.append(s)


def page(entry):
    key, url = entry
    try:
        raw, final, encoding = get(url)
        s = raw.decode(encoding, errors="replace")
        p = Page(final)
        p.feed(s)
        images = list({i["url"]: i for i in p.images}.values())
        # Preserve page source privately under QA for difficult lazy-loaded galleries.
        (QA / "pages").mkdir(exist_ok=True)
        (QA / "pages" / (key + ".html")).write_text(s, encoding="utf-8")
        return key, {"source": url, "resolved": final, "checked": "2026-11-17", "images": images, "links": p.links, "text": "\n".join(p.text)[-22000:]}
    except Exception as exc:
        return key, {"source": url, "error": str(exc)}


def photo(entry):
    from PIL import Image, ImageOps

    try:
        raw, final, _ = get(entry["url"])
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
        original = list(im.size)
        im.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        out = QA / "candidates"
        out.mkdir(exist_ok=True)
        target = out / (entry["id"] + ".webp")
        im.save(target, "WEBP", quality=86, method=6)
        return {**entry, "resolved": final, "originalSize": original, "width": im.width, "height": im.height, "path": str(target.relative_to(ROOT)), "sha256": hashlib.sha256(raw).hexdigest()}
    except Exception as exc:
        return {**entry, "error": str(exc)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=Path)
    parser.add_argument("--photos", type=Path)
    args = parser.parse_args()
    QA.mkdir(parents=True, exist_ok=True)
    if args.pages:
        sources = json.loads(args.pages.read_text(encoding="utf-8"))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            result = dict(pool.map(page, sources.items()))
        target = QA / (args.pages.stem + "-result.json")
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        for key, item in result.items():
            print(key, item.get("error") or f"{len(item['images'])} images; {item['resolved']}")
    if args.photos:
        photos = json.loads(args.photos.read_text(encoding="utf-8"))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            result = list(pool.map(photo, photos))
        target = QA / (args.photos.stem + "-result.json")
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        for item in result:
            print(item["id"], item.get("error") or f"{item['width']}x{item['height']}")


if __name__ == "__main__":
    main()
