"""Four bounded public-image probes: two curl and two urllib, no saved bodies.

Run after the listing phase. Selects four different 985px URLs whose local
photographs are still missing. HTTP/2 is requested only when curl supports it.
The urllib requests run in child processes so the 45-second total limit is real,
not a per-read socket timeout. This diagnostic never modifies production data.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
QA = Path(__file__).resolve().parent
AGENT = "Mozilla/5.0 (compatible; TONKO-Public-Catalog/1.0; public catalog research)"
HOST = "xn--80ajrmkna.xn--p1ai"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def valid_url(url):
    parts = urlsplit(url)
    return parts.scheme == "https" and parts.hostname == HOST and not parts.username and not parts.password and bool(re.fullmatch(r"/pics/cache/985_v_[0-9]+(?:_[0-9]+)?\.jpg", parts.path))


def urllib_child(url):
    start = time.monotonic()
    result = {"transport": "urllib", "httpStatus": 0, "sizeBytes": 0, "ok": False}
    try:
        if not valid_url(url):
            raise ValueError("Unexpected image URL")
        request = Request(url, headers={"User-Agent": AGENT, "Accept": "image/*"})
        with urlopen(request, timeout=45) as response:
            result.update({"httpStatus": response.status, "headersSeconds": round(time.monotonic() - start, 4), "httpVersion": str(response.version / 10)})
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                result["sizeBytes"] += len(chunk)
                if result["sizeBytes"] > 15_000_000:
                    raise ValueError("Image exceeded 15 MB")
            result["ok"] = response.status == 200
    except Exception as exc:
        if isinstance(exc, HTTPError):
            result["httpStatus"] = exc.code
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["totalSeconds"] = round(time.monotonic() - start, 4)
    print(json.dumps(result))


def probe(transport, url, curl_http2):
    start = time.monotonic()
    try:
        if transport == "curl":
            command = ["curl", "--silent", "--show-error", "--location", "--max-redirs", "3", "--proto", "=https", "--proto-redir", "=https", "--connect-timeout", "15", "--max-time", "45", "--user-agent", AGENT, "--header", "Accept: image/*", "--output", os.devnull, "--write-out", "%{json}"]
            if curl_http2:
                command.append("--http2")
            command.append(url)
            completed = subprocess.run(command, capture_output=True, text=True, timeout=45)
            raw = json.loads(completed.stdout) if completed.stdout.strip() else {}
            result = {"transport": transport, "httpStatus": int(raw.get("http_code", 0)), "httpVersion": raw.get("http_version"), "sizeBytes": int(raw.get("size_download", 0)), "ok": completed.returncode == 0 and int(raw.get("http_code", 0)) == 200, "exitCode": completed.returncode}
            for output, source in (("dnsSeconds", "time_namelookup"), ("connectSeconds", "time_connect"), ("tlsSeconds", "time_appconnect"), ("headersSeconds", "time_starttransfer"), ("totalSeconds", "time_total")):
                result[output] = raw.get(source)
            if completed.stderr.strip():
                result["error"] = completed.stderr.strip()[:1000]
        else:
            completed = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--urllib-child", url], capture_output=True, text=True, timeout=45)
            result = json.loads(completed.stdout)
        result["wallSeconds"] = round(time.monotonic() - start, 4)
        return result
    except Exception as exc:
        return {"transport": transport, "httpStatus": 0, "sizeBytes": 0, "ok": False, "wallSeconds": round(time.monotonic() - start, 4), "error": f"{type(exc).__name__}: {exc}"[:1000]}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=ROOT / "tights-guide/data/catalog.json")
    parser.add_argument("--output", type=Path, default=QA / "network-probe.json")
    args = parser.parse_args()
    data = json.loads(args.catalog.read_text("utf-8-sig"))
    available, seen = [], set()
    for item in data["items"]:
        url = item.get("imageSource") or ""
        if item.get("imageNeedsReview") or not valid_url(url) or url in seen:
            continue
        if item.get("image") and (ROOT / "tights-guide" / item["image"]).is_file():
            continue
        seen.add(url)
        available.append(item)
    # Spread across the remaining catalogue instead of selecting only its first
    # two failed old URLs. All four requests use different original source URLs.
    selected = [available[round(i * (len(available) - 1) / 3)] for i in range(4)] if len(available) >= 4 else available
    try:
        version = subprocess.check_output(["curl", "--version"], text=True, timeout=5)
        http2 = "HTTP2" in version
    except Exception as exc:
        version, http2 = str(exc), False
    report = {"startedAt": now(), "catalogCheckedAt": data.get("checkedAt"), "availableUnpicturedImages": len(available), "selectedCount": len(selected), "curlVersion": version.splitlines()[0] if version else "unavailable", "curlSupportsHttp2": http2, "requestLimitSeconds": 45, "requests": []}
    save(args.output, report)
    for index, item in enumerate(selected):
        transport = "curl" if index % 2 == 0 else "urllib"
        result = probe(transport, item["imageSource"], http2)
        report["requests"].append({"id": item["id"], "brand": item["brand"], "url": item["imageSource"], **result})
        save(args.output, report)
        print(f"{transport}: HTTP {result['httpStatus']}, {result['sizeBytes']} bytes, {result['wallSeconds']}s", flush=True)
        time.sleep(0.35)
    report["finishedAt"] = now()
    save(args.output, report)
    print(f"Saved {len(selected)} bounded transport probes to {args.output}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--urllib-child":
        urllib_child(sys.argv[2])
    else:
        main()
