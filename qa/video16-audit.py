"""Check release 16 provenance, reviewed previews and preserved deployed IDs."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from video_feed import classify, date, plain, stamp, validate_config
spec = importlib.util.spec_from_file_location("integrate16", ROOT / "qa/video16-integrate.py")
integrate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integrate)

VISUALLY_REVIEWED = {
    "iayHHSfIiKg", "QdHbpyNzSao", "5Z_E3EFnEUM", "If8WhJwiYsM", "UqqfxflUeKw",
    "zGJ9utIwP64", "RtnZIiNb7mo", "RrGZ5aHN0xY", "O3-nEUl9bFs", "eR21-yHN7cA",
    "ro2D5SMSwGY", "N4gBqi18clk", "0JYamXw7jiQ", "AY72V-uDWnI", "CZYpf9iATaw",
    "wx3TPfV7mGI", "651KEH195ZE", "6tPc0nykS_k", "_d3dURpReBo", "7aAdEV-V2yc",
    "V--1r2RysSc", "r1Z82-DVemY", "XcOu7MbJpwA", "s69QZjhN4eA", "pSNv4IEC1zc",
    "tYoCQxDY0lI", "b9X7XiQoZ44", "Y-S28ALI3ZE", "r1TSpXpRbhw",
}

EXISTING_SOURCE_PREVIEWS_REVIEWED = {
    "gKyG7hGU8bc", "ot7r6O_SGjw", "1gQQb9FLn68", "XVqDzhBhYJA", "Gu19TMOIV3Y",
    "1vZpMMS6KgE", "TMZK0s6QfTM",
    "xGYKQbuzp3c", "PtTiFnDl82A",
}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    now = datetime.now(timezone.utc)
    data = ROOT / "tights-guide/data"
    config = json.loads((data / "video-sources.json").read_text("utf-8"))
    videos = json.loads((data / "videos.json").read_text("utf-8"))
    baseline = json.loads((ROOT / "qa/video16-live-baseline.json").read_text("utf-8"))
    research = json.loads((ROOT / "qa/video16-research.json").read_text("utf-8"))
    validate_config(config)
    integrate.updater.validate_catalog(videos)
    by_id = {v["id"]: v for v in videos}
    assert len(by_id) == len(videos)
    assert set(baseline["ids"]) <= set(by_id), "Lost a deployed video"
    assert all((ROOT / "tights-guide" / v["thumbnail"]).is_file() for v in videos)
    channels = {c["handle"]: c for c in research["channels"]}
    samples = {v["id"]: v for v in research["videos"]}
    for handle, slug, _name, _language in integrate.SOURCES:
        source = next(s for s in config["sources"] if s["id"] == slug)
        channel = channels[handle]
        assert source["channelId"] == channel["channelId"]
        assert channel["feed"]["channelId"] in {source["channelId"], source["channelId"][2:]}
        sample = samples[source["verificationVideo"].split("v=")[-1]]["oembed"]
        assert sample["author_url"].casefold() in {u.casefold() for u in source["authorUrls"]}
    for handle, ident, *_ in integrate.REVIEWED:
        record, video = samples[ident], by_id[ident]
        assert ident in VISUALLY_REVIEWED
        assert video["originalTitle"] == plain(record["oembed"]["title"], 200)
        assert video["author"] == plain(record["oembed"]["author_name"], 100)
        assert video["thumbnailSource"] == record["oembed"]["thumbnail_url"]
        assert video["channelId"] == channels[handle]["channelId"]
        atom = next(e for e in channels[handle]["feed"]["entries"] if e["id"] == ident)
        assert video["publishedAt"] == stamp(date(atom["publishedAt"], now))
        assert video["dateSource"] == "youtube:atom.published"
        assert (ROOT / record["previewPath"]).read_bytes() == (ROOT / "tights-guide" / video["thumbnail"]).read_bytes()
    source_ids = {slug for _handle, slug, *_ in integrate.SOURCES}
    new_source_videos = [v for v in videos if v.get("sourceId") in source_ids]
    for video in new_source_videos:
        assert video["id"] in VISUALLY_REVIEWED, "Unreviewed new-source preview: " + video["id"]
        assert "http" not in video["description"].lower()

    decisions = []
    for channel in research["channels"]:
        handle = channel["handle"]
        policy = "archive-only" if handle == "legslavish" else "future-topic-monitoring" if handle == "OonaLinna" else "reviewed-selection-and-topic-feed"
        entries = []
        for entry in channel["feed"]["entries"]:
            ident = entry["id"]
            sample = samples.get(ident, {})
            topics = classify(entry["title"], entry["description"], profile="fashion-review")
            entries.append(dict(id=ident, title=entry["title"], publishedAt=entry["publishedAt"],
                titlePasses=bool(topics), withinAutomaticWindow=bool(date(entry["publishedAt"], now, config["maxAgeDays"])),
                oembedStatus=sample.get("oembedStatus", {}).get("status"),
                officialPreviewReviewed=ident in VISUALLY_REVIEWED, included=ident in by_id))
        decisions.append(dict(handle=handle, channelId=channel["channelId"], policy=policy,
            selectedVideos=[v["id"] for v in new_source_videos if v["authorUrl"].casefold() == channel["url"].casefold()] +
                (["iayHHSfIiKg"] if handle == "legslavish" else []), entries=entries))
    additions = [v for v in videos if v["id"] not in baseline["ids"]]
    assert all(v["id"] in VISUALLY_REVIEWED | EXISTING_SOURCE_PREVIEWS_REVIEWED for v in additions)
    report = dict(checkedAt=stamp(now), baselineTotal=baseline["total"], baselinePreserved=True,
        totalVideos=len(videos), sourceCount=len(config["sources"]), manualAdded=len(integrate.REVIEWED),
        additions=[dict(id=v["id"], author=v["author"], title=v["title"], addedBy=v.get("addedBy"), sourceId=v.get("sourceId")) for v in additions],
        channels=decisions,
        reviewedPreviewCount=len(VISUALLY_REVIEWED) + len(EXISTING_SOURCE_PREVIEWS_REVIEWED),
        existingSourcePreviewsReviewed=sorted(EXISTING_SOURCE_PREVIEWS_REVIEWED),
        reviewedPreviews=[dict(id=ident, sha256=hashlib.sha256((ROOT / samples[ident]["previewPath"]).read_bytes()).hexdigest()) for ident in sorted(VISUALLY_REVIEWED)])
    (ROOT / "qa/video16-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Verified", len(videos), "videos;", len(config["sources"]), "sources; all", baseline["total"], "deployed IDs preserved")
    print("New records:", len(additions), "; manual:", len(integrate.REVIEWED), "; official previews reviewed:", report["reviewedPreviewCount"])


if __name__ == "__main__":
    main()
