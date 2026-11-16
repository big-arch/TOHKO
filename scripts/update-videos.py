"""Refresh public videos; preserve the last published catalog on source failures.

No API key or manual editorial queue is required. Run before build-videos.py.
For CI use --deployed so consecutive scheduled deployments retain added videos
and source backoff state. A failure restoring the live snapshot fails the job.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlsplit

from video_feed import FetchError, collect, https_url, identity, validate_config

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "tights-guide"
DATA = SITE / "data"
PUBLIC = "https://big-arch.github.io/TOHKO/"


class Fetcher:
    """Bounded requests, verified TLS, and redirects restricted to known hosts."""
    def __init__(self, config):
        self.calls = 0
        self.hosts = {"www.youtube.com", "vimeo.com", "i.ytimg.com", "i.vimeocdn.com", "big-arch.github.io"}
        self.hosts.update(s["publisherHost"] for s in config["sources"] if s.get("publisherHost"))
        self.curl = shutil.which("curl.exe") or shutil.which("curl")
        if not self.curl:
            raise RuntimeError("curl is required (bundled with Windows / available on the CI runner)")

    def __call__(self, url, limit=4_000_000):
        for _ in range(3):
            if not https_url(url, self.hosts):
                raise ValueError("Fetch URL is outside the HTTPS allowlist")
            self.calls += 1
            if self.calls > 90:
                raise FetchError()
            try:
                result = subprocess.run([
                    self.curl, "--silent", "--show-error", "--compressed", "--proto", "=https",
                    "--connect-timeout", "8", "--max-time", "22", "--max-filesize", str(limit),
                    "--user-agent", "TONKO-Videos/1.0 (+https://big-arch.github.io/TOHKO/)",
                    "--write-out", "\n%{http_code}\n%{redirect_url}", url,
                ], capture_output=True, timeout=27)
            except (subprocess.TimeoutExpired, OSError) as error:
                raise FetchError() from error
            parts = result.stdout.rsplit(b"\n", 2)
            if len(parts) != 3:
                raise FetchError()
            body, raw_code, redirect = parts
            code = int(raw_code) if raw_code.isdigit() else 0
            if result.returncode or len(body) > limit:
                raise FetchError(code)
            if code in {301, 302, 303, 307, 308}:
                # Do not follow a redirect until its destination has been checked.
                url = redirect.decode("utf-8", "strict")
                continue
            if not 200 <= code < 300:
                raise FetchError(code)
            return body
        raise FetchError()


def validate_catalog(videos):
    if not isinstance(videos, list) or len(videos) > 200:
        raise ValueError("Invalid video snapshot")
    seen = set()
    for video in videos:
        if not isinstance(video, dict) or video.get("id") in seen:
            raise ValueError("Invalid or duplicate video in snapshot")
        seen.add(video["id"])
        if video.get("addedBy") == "feed":
            parsed = identity(video.get("url", ""))
            expected = ("vimeo-" if parsed and parsed[0] == "vimeo" else "") + (parsed[1] if parsed else "")
            if not parsed or video["id"] != expected or video.get("provider") != parsed[0]:
                raise ValueError("Invalid automatic video identity")
            if not re.fullmatch(r"assets/videos-new/" + re.escape(video["id"]) + r"\.(?:jpg|png|webp)", video.get("thumbnail", "")):
                raise ValueError("Invalid automatic thumbnail path")
            if not https_url(video.get("thumbnailSource", ""), {"i.ytimg.com", "i.vimeocdn.com"}):
                raise ValueError("Invalid thumbnail CDN")
    return videos


def restore_previous(seed, fetch):
    try:
        deployed = validate_catalog(json.loads(fetch(PUBLIC + "data/videos.json")))
    except FetchError as error:
        if error.status == 404:
            return seed, {}
        raise  # Never deploy the repository seed over an unreachable live history.
    try:
        state = json.loads(fetch(PUBLIC + "data/video-feed-state.json"))
        if state.get("version") != 1 or not isinstance(state.get("sources"), list):
            raise ValueError("Invalid deployed video source state")
    except FetchError as error:
        if error.status != 404:
            raise
        state = {}  # First deployment of the updater on an existing video library.
    # Repository-curated records win; retain every deployed automatic record.
    local = {video["id"] for video in seed}
    return seed + [video for video in deployed if video["id"] not in local], state


def image_extension(raw):
    if raw.startswith(b"\xff\xd8\xff") and raw.endswith(b"\xff\xd9"):
        return ".jpg"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        return ".webp"
    raise ValueError("Expected an image from the official thumbnail CDN")


def atomic_write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(raw)
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployed", action="store_true", help="Restore live catalog and source backoff before collection")
    parser.add_argument("--force", action="store_true", help="Retry sources immediately; normally honor exponential backoff")
    args = parser.parse_args()
    config = json.loads((DATA / "video-sources.json").read_text("utf-8"))
    validate_config(config)
    previous = validate_catalog(json.loads((DATA / "videos.json").read_text("utf-8")))
    state_path = DATA / "video-feed-state.json"
    state = json.loads(state_path.read_text("utf-8")) if state_path.exists() else {}
    fetch = Fetcher(config)
    if args.deployed:
        previous, state = restore_previous(previous, fetch)
        # Previous CI runs deploy their own preview files. Restore those local
        # assets before building, even when the upstream video source is down.
        for video in previous:
            if video.get("addedBy") != "feed" or (SITE / video["thumbnail"]).is_file():
                continue
            raw = fetch(PUBLIC + video["thumbnail"], limit=8_000_000)
            if image_extension(raw) != Path(video["thumbnail"]).suffix:
                raise ValueError("Deployed preview type mismatch")
            atomic_write(SITE / video["thumbnail"], raw)

    def thumbnail(video):
        raw = fetch(video["thumbnailSource"], limit=8_000_000)
        relative = "assets/videos-new/" + video["id"] + image_extension(raw)
        atomic_write(SITE / relative, raw)
        return relative

    now = datetime.now(timezone.utc)
    catalog, result = collect(config, previous, state, fetch, thumbnail, now, args.force)
    validate_catalog(catalog)
    for video in catalog:
        if not (SITE / video["thumbnail"]).is_file():
            raise ValueError("Missing preview; refusing an incomplete catalog")
    if not catalog:
        raise RuntimeError("No usable video snapshot available")
    # Write only after all validation and preview restoration succeed.
    atomic_write(DATA / "videos.json", (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    atomic_write(state_path, (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    for source in result["sources"]:
        print(f"{source['name']}: {source['status']}; candidates={source.get('candidates', 0)}; added={source['added']}; rejected={source.get('rejected', 0)}")
    print(f"Videos: {len(catalog)}; added: {result['added']}; network requests: {fetch.calls}")


if __name__ == "__main__":
    main()
