"""Conservative, keyless discovery from an explicit publisher allowlist.

Only public Atom + official oEmbed endpoints are used. oEmbed confirms an
available embed, not playback in every visitor's region/network. Never scrape
watch-page internals, follow arbitrary feed links or work around authentication.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
import json
import re
from urllib.parse import parse_qs, urlencode, urlsplit
import xml.etree.ElementTree as ET

NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "m": "http://search.yahoo.com/mrss/"}
YT_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
VIMEO_ID = re.compile(r"\d{6,12}\Z")
SUBJECT = re.compile(r"\b(?:tights?|hosiery|pantyhose|stockings?|leggings?)\b|колгот|чулк|легинс", re.I)
EXCLUDED = re.compile(r"\b(?:nude|naked|fetish|onlyfans|porn|nsfw|lingerie|bikini|swimwear)\b|обнаж|эрот|фетиш|нижнее бель|купальник", re.I)
TOPICS = (
    ("making", r"\b(?:manufactur\w*|production|factory|craftsmanship|recycl\w*|thread|knitting)\b|производств|фабрик|вязани"),
    ("choice", r"\b(?:how to|size|fit|choose|choosing|coverage|denier|thermal|shaping|sheer|opaque|invisible)\b|как (?:выбрать|носить)|размер|плотност"),
    ("reviews", r"\breviews?\b|обзор|сравнен"),
    ("tryon", r"\btry[ -]?on\b|примерк"),
    ("asmr", r"\basmr\b|асмр"),
    ("styling", r"\b(?:styl\w*|outfit\w*|fashion|look\w*|collection)\b|образ|сочетан|стил|коллекц"),
)


class FetchError(OSError):
    def __init__(self, status=0):
        super().__init__(f"HTTP {status}" if status else "network unavailable")
        self.status = status


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.embeds, self.suppressed = [], [], 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style"}:
            self.suppressed += 1
        if tag == "iframe" and attrs.get("src"):
            self.embeds.append(attrs["src"])

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.suppressed:
            self.suppressed -= 1

    def handle_data(self, value):
        if not self.suppressed:
            self.parts.append(value)


def plain(value, limit=1000):
    parser = TextParser()
    parser.feed(str(value or ""))
    text = re.sub(r"\s+", " ", unescape(" ".join(parser.parts))).strip()
    if len(text) <= limit:
        return text
    return text[:limit-1].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def date(value, now, max_age=None):
    """Require a real, unambiguous timestamp; never substitute the fetch date."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return None
    if parsed.tzinfo is None or parsed > now + timedelta(minutes=5):
        return None
    if max_age is not None and parsed < now - timedelta(days=max_age):
        return None
    return parsed.astimezone(timezone.utc)


def stamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def https_url(value, hosts):
    try:
        url = urlsplit(value)
        return (url.scheme == "https" and url.hostname in hosts and
                url.port in (None, 443) and not url.username and not url.password)
    except (ValueError, TypeError):
        return False


def identity(url):
    """Canonical provider identity, with exact hosts (never suffix matching)."""
    if not https_url(url, {"www.youtube.com", "youtube.com", "www.youtube-nocookie.com", "youtu.be", "vimeo.com", "player.vimeo.com"}):
        return None
    p = urlsplit(url)
    ident = None
    if p.hostname in {"www.youtube.com", "youtube.com", "www.youtube-nocookie.com", "youtu.be"}:
        if p.hostname == "youtu.be":
            ident = p.path.removeprefix("/")
        elif p.path == "/watch":
            ident = parse_qs(p.query).get("v", [""])[0]
        elif p.path.startswith(("/embed/", "/shorts/")):
            ident = p.path.split("/")[-1]
        if ident and YT_ID.fullmatch(ident):
            return "youtube", ident, "https://www.youtube.com/watch?v=" + ident
    elif p.hostname in {"vimeo.com", "player.vimeo.com"}:
        ident = p.path.removeprefix("/video/") if p.hostname == "player.vimeo.com" else p.path.removeprefix("/")
        # Private/unlisted hash URLs are deliberately excluded from this public feed.
        if VIMEO_ID.fullmatch(ident) and not parse_qs(p.query).get("h"):
            return "vimeo", ident, "https://vimeo.com/" + ident
    return None


def classify(title, description="", publisher=False):
    # Channel descriptions often mention tights on unrelated videos: require the
    # subject in the title. A publisher Atom entry has a specific article body.
    text = title + " " + description
    evidence = text if publisher else title
    if not SUBJECT.search(evidence) or EXCLUDED.search(title):
        return []
    topics = [name for name, pattern in TOPICS if re.search(pattern, text, re.I)]
    return topics[:3] or ["choice"]


def validate_config(config):
    if config.get("version") != 1 or not isinstance(config.get("sources"), list):
        raise ValueError("Invalid video source configuration")
    ids = set()
    for source in config["sources"]:
        if source["id"] in ids or not re.fullmatch(r"[a-z0-9-]+", source["id"]):
            raise ValueError("Duplicate/invalid source ID")
        ids.add(source["id"])
        if source["kind"] == "youtube-atom":
            channel = source.get("channelId", "")
            expected = "https://www.youtube.com/feeds/videos.xml?channel_id=" + channel
            if not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", channel) or source["url"] != expected:
                raise ValueError("YouTube source must be its verified channel feed")
        elif source["kind"] == "publisher-atom":
            if not https_url(source["url"], {source["publisherHost"]}):
                raise ValueError("Publisher feed must stay on its verified domain")
        else:
            raise ValueError("Unsupported video source")
        if not source.get("authorUrls") or any(not https_url(u, {"www.youtube.com", "vimeo.com"}) for u in source["authorUrls"]):
            raise ValueError("Each publisher needs verified platform author URLs")
    for name, low, high in (("maxAutoVideos", 1, 100), ("maxNewPerRun", 1, 20),
                            ("maxCandidatesPerSource", 1, 30), ("maxAgeDays", 1, 730)):
        if type(config.get(name)) is not int or not low <= config[name] <= high:
            raise ValueError("Invalid bound: " + name)


def candidates(raw, source, now, max_age):
    if len(raw) > 4_000_000 or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("Unsafe or oversized feed")
    root = ET.fromstring(raw)
    if root.tag != "{" + NS["a"] + "}feed":
        raise ValueError("Expected an Atom feed")
    if source["kind"] == "youtube-atom":
        # Public channel feeds currently omit UC in the root, while entry-level
        # IDs keep it. Accept only these two exact forms of the allowed channel.
        root_channel = root.findtext("yt:channelId", "", NS)
        if root_channel not in {source["channelId"], source["channelId"][2:]}:
            raise ValueError("Feed channel does not match the allowlist")
    result, seen = [], set()
    for entry in root.findall("a:entry", NS)[:100]:
        published = date(entry.findtext("a:published", "", NS), now, max_age)
        title = plain(entry.findtext("a:title", "", NS), 200)
        if not published or not title:
            continue
        alternate = next((el.attrib.get("href", "") for el in entry.findall("a:link", NS)
                          if el.attrib.get("rel", "alternate") == "alternate"), "")
        is_publisher = source["kind"] == "publisher-atom"
        if is_publisher:
            if not https_url(alternate, {source["publisherHost"]}):
                continue
            content = entry.findtext("a:content", "", NS)
            parser = TextParser()
            parser.feed(content)
            links, description = parser.embeds, plain(content, 4000)
        else:
            if entry.findtext("yt:channelId", "", NS) != source["channelId"]:
                continue
            links = [alternate]
            description = plain(entry.findtext("m:group/m:description", "", NS), 1000)
        topics = classify(title, description, is_publisher)
        if not topics:
            continue
        for link in links:
            parsed = identity(link)
            if not parsed or parsed[:2] in seen:
                continue
            provider, video_id, canonical = parsed
            if not is_publisher and (provider != "youtube" or video_id != entry.findtext("yt:videoId", "", NS)):
                continue
            seen.add(parsed[:2])
            result.append(dict(provider=provider, providerId=video_id, url=canonical,
                               title=title, description=description, topics=topics,
                               publishedAt=stamp(published), sourceUrl=alternate,
                               publisherArticle=is_publisher))
    return sorted(result, key=lambda c: c["publishedAt"], reverse=True)


def oembed_url(candidate):
    endpoint = "https://www.youtube.com/oembed" if candidate["provider"] == "youtube" else "https://vimeo.com/api/oembed.json"
    return endpoint + "?" + urlencode({"url": candidate["url"], "format": "json", "maxwidth": 960})


def verify(candidate, source, raw, now, max_age):
    """Validate embed/author; copy metadata, never execute provider HTML."""
    data = json.loads(raw)
    if data.get("type") != "video" or data.get("author_url", "").rstrip("/").casefold() not in {
        value.rstrip("/").casefold() for value in source["authorUrls"]
    }:
        raise ValueError("oEmbed author is not an allowed publisher")
    parser = TextParser()
    parser.feed(data.get("html", ""))
    expected = (candidate["provider"], candidate["providerId"])
    def official_embed(url):
        parsed = urlsplit(url)
        if candidate["provider"] == "youtube":
            return (parsed.hostname in {"www.youtube.com", "www.youtube-nocookie.com"} and
                    parsed.path == "/embed/" + candidate["providerId"])
        return parsed.hostname == "player.vimeo.com" and parsed.path == "/video/" + candidate["providerId"]
    if not any(identity(url) and identity(url)[:2] == expected and official_embed(url) for url in parser.embeds):
        raise ValueError("oEmbed has no matching official iframe")
    thumb = data.get("thumbnail_url", "")
    if not https_url(thumb, {"i.ytimg.com", "i.vimeocdn.com"}):
        raise ValueError("Thumbnail is outside the official CDN allowlist")
    title = plain(data.get("title"), 200)
    if not title or EXCLUDED.search(title):
        raise ValueError("Invalid or excluded video title")
    published = candidate["publishedAt"]
    date_source = "youtube:atom.published"
    if candidate["provider"] == "vimeo":
        # Vimeo oEmbed's upload_date has no time-zone suffix: publish only its
        # calendar date rather than inventing a timezone/precise timestamp.
        uploaded = data.get("upload_date", "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", uploaded):
            raise ValueError("Vimeo upload date missing")
        if not date(uploaded[:10] + "T00:00:00Z", now, max_age):
            raise ValueError("Vimeo upload date outside the allowed interval")
        published, date_source = uploaded[:10], "vimeo:oembed.upload_date (date only)"
        if str(data.get("video_id")) != candidate["providerId"]:
            raise ValueError("Vimeo video ID mismatch")
    elif not classify(title):
        raise ValueError("oEmbed title no longer matches the topic")
    is_article = candidate["publisherArticle"]
    # A journal title is more readable than a CMS filename, but keep the
    # original provider title and article URL alongside it.
    display_title = candidate["title"] if is_article else title
    description = plain(data.get("description") or candidate["description"], 300)
    if not description:
        description = f"Видео {plain(data.get('author_name'), 100)}: {display_title}."
    provider, video_id = expected
    ident = "vimeo-" + video_id if provider == "vimeo" else video_id
    result = dict(id=ident, provider=provider, title=display_title, originalTitle=title,
                  description=description, topics=candidate["topics"], language="original",
                  kind="Видео издателя" if is_article else "Видео канала",
                  author=plain(data.get("author_name"), 100), authorUrl=data["author_url"],
                  url=candidate["url"], thumbnailSource=thumb,
                  thumbnailWidth=int(data.get("thumbnail_width", 480)),
                  thumbnailHeight=int(data.get("thumbnail_height", 360)),
                  publishedAt=published, dateSource=date_source, sourceId=source["id"],
                  sourceUrl=candidate["sourceUrl"], addedBy="feed", discoveredAt=stamp(now),
                  checked=now.date().isoformat(), embedCheckedAt=stamp(now), embedStatus="oembed")
    if provider == "vimeo":
        result["providerId"] = video_id
        if isinstance(data.get("duration"), (int, float)) and 0 < data["duration"] < 86400:
            result["duration"] = data["duration"]
    return result


def dedup_key(item):
    return (re.sub(r"\W+", "", item.get("originalTitle", item.get("title", "")).casefold()),
            re.sub(r"\W+", "", item.get("author", "").casefold()))


def collect(config, previous, state, fetch, store_thumbnail, now, force=False):
    validate_config(config)
    old_states = {s["id"]: s for s in state.get("sources", [])}
    output = list(previous)
    existing = {v["id"] for v in output}
    keys = {dedup_key(v) for v in output}
    report, total_added, total_success = [], 0, 0
    for source in config["sources"]:
        old = old_states.get(source["id"], {})
        status = {**old, "id": source["id"], "name": source["name"], "url": source["url"]}
        retry = date(old.get("nextRetryAt"), now + timedelta(days=8))
        if retry and retry > now and not force:
            report.append({**status, "status": "backoff", "added": 0})
            continue
        status.update(lastAttemptAt=stamp(now), added=0, candidates=0, rejected=0)
        try:
            found = candidates(fetch(source["url"]), source, now, config["maxAgeDays"])
            status["candidates"] = len(found)
            transient = None
            for candidate in found[:config["maxCandidatesPerSource"]]:
                ident = ("vimeo-" if candidate["provider"] == "vimeo" else "") + candidate["providerId"]
                if ident in existing or total_added >= config["maxNewPerRun"]:
                    continue
                try:
                    video = verify(candidate, source, fetch(oembed_url(candidate)), now, config["maxAgeDays"])
                    if dedup_key(video) in keys:
                        continue
                    video["thumbnail"] = store_thumbnail(video)
                except FetchError as error:
                    status["rejected"] += 1
                    if error.status in {0, 429} or error.status >= 500:
                        transient = error
                        break  # Respect upstream throttling; do not hammer the rest.
                    continue
                except (ValueError, KeyError, TypeError):
                    status["rejected"] += 1
                    continue
                output.append(video)
                existing.add(video["id"])
                keys.add(dedup_key(video))
                total_added += 1
                status["added"] += 1
            if transient:
                raise transient
            status.update(status="ok", failures=0, lastSuccessfulAt=stamp(now), nextRetryAt=None, error=None)
            total_success += 1
        except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as error:
            failures = min(int(old.get("failures", 0)) + 1, 8)
            code = getattr(error, "status", None)
            status.update(status="error", failures=failures,
                          error="HTTP " + str(code) if code else "feed or metadata unavailable",
                          nextRetryAt=stamp(now + timedelta(hours=min(2 ** failures, 48))))
        report.append(status)
    fixed = [v for v in output if v.get("addedBy") != "feed"]
    automatic = sorted((v for v in output if v.get("addedBy") == "feed"),
                       key=lambda v: (v.get("publishedAt", ""), v["id"]), reverse=True)[:config["maxAutoVideos"]]
    # Keep direct public brand videos first; show fresh additions ahead of the
    # older selection without rewriting or deleting any curated record.
    catalog = [v for v in fixed if v.get("provider") == "native"] + automatic + [v for v in fixed if v.get("provider") != "native"]
    next_state = dict(version=1, checkedAt=stamp(now),
                      lastSuccessfulAt=stamp(now) if total_success else state.get("lastSuccessfulAt"),
                      added=total_added, autoVideos=len(automatic), totalVideos=len(catalog), sources=report)
    return catalog, next_state
