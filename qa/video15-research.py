"""One-off release 15 research: public metadata only, never video media.

Only official oEmbed, public HTML metadata tags and Atom feeds are read.
No watch-page scripts, private APIs, authentication or access workarounds.
The result is evidence for the manual archive import, not a CI discovery path.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa/video15-research.json"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "m": "http://search.yahoo.com/mrss/"}
REQUESTS = [
    ("Светлана Макарова", "G6m9vzvaGoc", "UC1DZTK2DAylpWtucMcZSXOw"),
    ("Анастасия Оделс", "yqTK5Gs0qmA", "UCtuUdhlMTAz9dleiMB3v58w"),
    ("Лирия Хольдина", "qlPJ4PhnNWo", ""),
    ("Olga_Delevsky", "yJ_D-39z7eg", ""),
    ("KseniyaShirshova", "24E0r4MRLuI", ""),
    ("Cassie Clarke", "fVNOZltsqo4", ""),
    ("Kerina Wang", "I85twyDA_-g", ""),
    ("Kerina Wang", "fVRy95vrAZ4", ""),
    ("CalzedoniaOfficial", "8ruf9D3Cu4c", "UCoZE4fZMjf0CbZGBlbneNDQ"),
    ("Luxe Mia ASMR", "TVDNAIs4N7Q", ""),
    ("ASMR by Chinese Girl", "0GwaAwg5NCA", ""),
    ("Sweet Deep ASMR", "kzbUxpc-vkQ", ""),
    ("ASMR Kate Lullaby", "FvqmyWTU3bM", ""),
    ("Sleepy Beauty ASMR", "sVlD9Ok0xy0", ""),
    ("Russian ASMR (anonymous request)", "zu8UTjg3E4U", ""),
    ("Больше чем стиль", "adj7nIdbrXc", ""),
    ("layla (not Layla Fashion)", "FVDXcK_7HVo", ""),
    ("Annika Victoria", "jAovDlIn6CA", ""),
    ("Tinkerbell", "vbIbX589Idc", ""),
    ("Multi-brand test", "Lhb91O9w5wk", ""),
    ("Sheertex test", "s5RVt62Scgc", ""),
    ("Kira's Nylons", "MD_NUowADjw", ""),
    ("Gentle Whispering ASMR (additional textile research)", "599LMnGLC9k", ""),
    ("WhispersRed ASMR (additional textile research)", "l790AoYh1HE", ""),
]
CHANNELS = [
    ("TightsTV The Tight Spot", "https://www.youtube.com/channel/UCdGZ5AxDylcpE8fW2cwmQBw"),
    ("Layla Fashion", "https://www.youtube.com/@layla_fashion"),
    ("Sheertex", "https://www.youtube.com/@sheertex"),
    ("Glamissima", "https://www.youtube.com/@Glamissima"),
    ("Cassie Clarke", "https://www.youtube.com/@cassieclarke"),
    ("ASMR by Chinese Girl", "https://www.youtube.com/@ASMRbyChineseGirl"),
    ("Sweet Deep ASMR", "https://www.youtube.com/@sweetdeepasmr"),
    ("ASMR Fuyu (existing selection)", "https://www.youtube.com/@asmrfuyu800"),
    ("Gentle Whispering ASMR (additional textile research)", "https://www.youtube.com/@GentleWhisperingASMR"),
    ("WhispersRed ASMR (additional textile research)", "https://www.youtube.com/@WhispersRedASMR"),
]


def fetch(url):
    try:
        result = subprocess.run([
            "curl.exe", "--silent", "--show-error", "--compressed", "--proto", "=https",
            "--connect-timeout", "8", "--max-time", "22", "--max-filesize", "6000000",
            "--user-agent", "TONKO-Videos/1.0 (+https://big-arch.github.io/TOHKO/)",
            "--write-out", "\n%{http_code}", url,
        ], capture_output=True, timeout=27)
    except (subprocess.TimeoutExpired, OSError):
        return {"status": 0, "error": "network unavailable"}, b""
    parts = result.stdout.rsplit(b"\n", 1)
    code = int(parts[-1]) if len(parts) == 2 and parts[-1].isdigit() else 0
    if result.returncode or code != 200:
        return {"status": code, "error": "HTTP " + str(code) if code else "network unavailable"}, b""
    return {"status": code}, parts[0]


class PublicMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values, self.feeds, self.canonical = {}, [], ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = attrs.get("itemprop") or attrs.get("property") or attrs.get("name")
            if key in {"name", "datePublished", "uploadDate", "duration", "channelId", "og:title", "og:url"}:
                self.values[key] = attrs.get("content", "")
        if tag == "link":
            if attrs.get("type") == "application/rss+xml":
                self.feeds.append(attrs.get("href", ""))
            if attrs.get("rel") == "canonical":
                self.canonical = attrs.get("href", "")


def metadata(url):
    info, raw = fetch(url)
    if raw:
        parser = PublicMetadata()
        parser.feed(raw.decode("utf-8", "replace"))
        info.update(metadata=parser.values, feeds=parser.feeds, canonical=parser.canonical)
    return {"url": url, **info}


def video(item):
    name, ident, expected = item
    url = "https://www.youtube.com/watch?v=" + ident
    endpoint = "https://www.youtube.com/oembed?" + urlencode({"url": url, "format": "json"})
    info, raw = fetch(endpoint)
    record = dict(requested=name, id=ident, expectedChannelId=expected, url=url, oembedUrl=endpoint, oembedStatus=info)
    if raw:
        try:
            record["oembed"] = json.loads(raw)
        except ValueError:
            record["oembedStatus"]["error"] = "invalid JSON"
        # Watch pages redirected to CAPTCHA during research. Do not request
        # them again: archival dates come from public Atom / indexed originals.
    print(ident, info.get("status"), record.get("oembed", {}).get("title", "unavailable"), flush=True)
    return record


def channel(item):
    name, url = item
    info = metadata(url)
    channel_id = info.get("metadata", {}).get("channelId", "")
    for value in info.get("feeds", []) + [info.get("canonical", ""), url]:
        match = re.search(r"(?:channel_id=|/channel/)(UC[A-Za-z0-9_-]{22})(?:[&/?]|$)", value)
        if match:
            channel_id = match[1]
            break
    record = {"name": name, "url": url, "channelId": channel_id, "publicPage": info}
    if channel_id:
        feed_url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + channel_id
        status, raw = fetch(feed_url)
        record["feed"] = {"url": feed_url, **status}
        if raw:
            try:
                root = ET.fromstring(raw)
                record["feed"].update(
                    channelId=root.findtext("yt:channelId", "", NS),
                    title=root.findtext("a:title", "", NS),
                    author=root.findtext("a:author/a:name", "", NS),
                    entries=[dict(id=e.findtext("yt:videoId", "", NS), title=e.findtext("a:title", "", NS),
                                  publishedAt=e.findtext("a:published", "", NS))
                             for e in root.findall("a:entry", NS)],
                )
            except ET.ParseError:
                record["feed"]["error"] = "not Atom XML"
    print("Channel", channel_id or "unresolved", name, flush=True)
    return record


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--retry-transient" in sys.argv:
        result = json.loads(OUT.read_text("utf-8"))
        with ThreadPoolExecutor(max_workers=3) as pool:
            retry_items = [(v["requested"], v["id"], v["expectedChannelId"]) for v in result["videos"] if v["oembedStatus"]["status"] == 0]
            replacements = {v["id"]: v for v in pool.map(video, retry_items)}
            result["videos"] = [replacements.get(v["id"], v) for v in result["videos"]]
            targets = {c["url"]: c["name"] for c in result["channels"] if c.get("feed", {}).get("status") == 0}
            known = {c["url"] for c in result["channels"]}
            for v in result["videos"]:
                data = v.get("oembed", {})
                if data.get("author_url") and data["author_url"] not in known:
                    targets[data["author_url"]] = data["author_name"]
            replacements = {c["url"]: c for c in pool.map(channel, [(n, u) for u, n in targets.items()])}
            result["channels"] = [replacements.get(c["url"], c) for c in result["channels"]]
            result["channels"] += [c for u, c in replacements.items() if u not in known]
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    result = {"checkedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "videos": [], "channels": []}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for record in pool.map(video, REQUESTS):
            result["videos"].append(record)
            OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        targets = {url: name for name, url in CHANNELS}
        for item in result["videos"]:
            embed = item.get("oembed", {})
            if embed.get("author_url", "").startswith("https://www.youtube.com/"):
                targets[embed["author_url"]] = embed["author_name"]
            if item["expectedChannelId"]:
                targets["https://www.youtube.com/channel/" + item["expectedChannelId"]] = item["requested"]
        for record in pool.map(channel, [(name, url) for url, name in targets.items()]):
            result["channels"].append(record)
            OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Saved", OUT)


if __name__ == "__main__":
    main()
