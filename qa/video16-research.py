"""Release 16: public channel metadata / Atom / oEmbed evidence only.

No video downloads, private APIs, watch-page scripts, CAPTCHA or login bypass.
Channel resolution is restricted to public HTML metadata and the RSS link.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "qa/video16-research.json"
spec = importlib.util.spec_from_file_location("research15", ROOT / "qa/video15-research.py")
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
NS = old.NS
CHANNELS = ["legslavish", "PoppyAttic", "Dashadaiz", "funkyredfoxx", "FunhoseStudios", "legsbylayla", "OonaLinna", "peytonkinsly"]


def channel(handle):
    url = "https://www.youtube.com/@" + handle
    page = old.metadata(url)
    ident = page.get("metadata", {}).get("channelId", "")
    for value in page.get("feeds", []) + [page.get("canonical", "")]:
        match = re.search(r"(?:channel_id=|/channel/)(UC[A-Za-z0-9_-]{22})(?:[&/?]|$)", value)
        if match:
            ident = match[1]
            break
    record = dict(handle=handle, url=url, channelId=ident, publicPage=page)
    if ident:
        feed_url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + ident
        status, raw = old.fetch(feed_url)
        record["feed"] = {"url": feed_url, **status}
        if raw:
            try:
                root = ET.fromstring(raw)
                record["feed"].update(channelId=root.findtext("yt:channelId", "", NS),
                    author=root.findtext("a:author/a:name", "", NS),
                    title=root.findtext("a:title", "", NS),
                    entries=[dict(id=e.findtext("yt:videoId", "", NS),
                        channelId=e.findtext("yt:channelId", "", NS),
                        title=e.findtext("a:title", "", NS),
                        publishedAt=e.findtext("a:published", "", NS),
                        description=e.findtext("m:group/m:description", "", NS),
                        thumbnail=e.find("m:group/m:thumbnail", NS).attrib if e.find("m:group/m:thumbnail", NS) is not None else {})
                        for e in root.findall("a:entry", NS)])
            except ET.ParseError:
                record["feed"]["error"] = "not Atom XML"
    print(handle, ident or "unresolved", "page", page.get("status"), "feed", record.get("feed", {}).get("status"), flush=True)
    return record


def video(ident):
    url = "https://www.youtube.com/watch?v=" + ident
    endpoint = "https://www.youtube.com/oembed?" + urlencode({"url": url, "format": "json"})
    info, raw = old.fetch(endpoint)
    record = dict(id=ident, url=url, oembedUrl=endpoint, oembedStatus=info)
    if raw:
        record["oembed"] = json.loads(raw)
    print(ident, info.get("status"), record.get("oembed", {}).get("title", "unavailable"), flush=True)
    return record


def preview(record):
    embed = record.get("oembed", {})
    url = embed.get("thumbnail_url", "")
    if not url.startswith("https://i.ytimg.com/"):
        return record
    info, raw = old.fetch(url)
    record["previewStatus"] = info
    if raw and raw.startswith(b"\xff\xd8\xff") and raw.endswith(b"\xff\xd9"):
        target = ROOT / "qa/video16-previews" / (record["id"] + ".jpg")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        record["previewPath"] = str(target.relative_to(ROOT)).replace("\\", "/")
    print("Preview", record["id"], info.get("status"), flush=True)
    return record


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    result = json.loads(OUT.read_text("utf-8")) if OUT.exists() else dict(channels=[], videos=[])
    result["checkedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with ThreadPoolExecutor(max_workers=3) as pool:
        if "--previews" in sys.argv:
            targets = set(sys.argv[sys.argv.index("--previews") + 1:])
            replaces = {v["id"]: v for v in pool.map(preview, [v for v in result["videos"] if not targets or v["id"] in targets])}
            result["videos"] = [replaces.get(v["id"], v) for v in result["videos"]]
        elif "--videos" in sys.argv:
            ids = sys.argv[sys.argv.index("--videos") + 1:]
            replaces = {v["id"]: v for v in pool.map(video, ids)}
            known = {v["id"] for v in result["videos"]}
            result["videos"] = [replaces.get(v["id"], v) for v in result["videos"]]
            result["videos"] += [v for ident, v in replaces.items() if ident not in known]
        else:
            handles = CHANNELS if "--retry" not in sys.argv else [c["handle"] for c in result["channels"] if not c.get("channelId") or c.get("feed", {}).get("status") == 0]
            replaces = {c["handle"]: c for c in pool.map(channel, handles)}
            known = {c["handle"] for c in result["channels"]}
            result["channels"] = [replaces.get(c["handle"], c) for c in result["channels"]]
            result["channels"] += [c for handle, c in replaces.items() if handle not in known]
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Saved", OUT)


if __name__ == "__main__":
    main()
