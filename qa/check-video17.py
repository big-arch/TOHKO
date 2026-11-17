"""Release 17 Chrome QA. Local HTTP only; every external request is aborted.

Uses a fixed clock for repeatable 7-day boundaries. Source media playback is not
tested: the Snag control/URL are checked without fetching the stream.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import functools
import json
from pathlib import Path
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "tights-guide"
OUTPUT = ROOT / "qa/video17-ui"
NOW = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
for runtime in (ROOT / ".cache/pw-runtime", Path("C:/Users/Артур/Documents/CODEX_сайт_ТОНКО/.cache/pw-runtime")):
    if runtime.is_dir():
        sys.path.insert(0, str(runtime))
        break
from playwright.sync_api import expect, sync_playwright
from test_video17 import builder

VIDEOS = json.loads((SITE / "data/videos.json").read_text("utf-8"))
SOURCES = json.loads((SITE / "data/video-sources.json").read_text("utf-8"))["sources"]
CHANNELS = builder.build_channels(VIDEOS, SOURCES)


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(SITE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    checks, errors, blocked = [], [], []

    def route_local(route):
        if route.request.url.startswith(origin + "/"):
            route.continue_()
        else:
            blocked.append(route.request.url)
            route.abort()

    def prepare(context):
        context.route("**/*", route_local)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.clock.install(time=NOW - timedelta(minutes=1))
        page.clock.pause_at(NOW)
        return page

    def ids(page):
        return page.locator("[data-video-card]:visible").evaluate_all("nodes=>nodes.map(n=>n.dataset.videoCard)")

    def expected(videos=VIDEOS, order="newest"):
        return [v["id"] for v in builder.sorted_videos(videos, order)]

    def expect_ids(page, values):
        expect(page.locator("[data-video-card]:visible")).to_have_count(len(values))
        assert ids(page) == values, (ids(page), values)

    def no_overflow(page):
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), page.viewport_size
        assert not page.locator(".video-tools, .video-channel-row select, .video-card:visible, .video-feature").evaluate_all(
            "nodes=>nodes.filter(n=>n.getBoundingClientRect().right>innerWidth+.5 || n.getBoundingClientRect().left<-.5).map(n=>n.className || n.id)")

    def new_ids(page):
        return set(page.locator(".video-card [data-video-new]:visible").evaluate_all("nodes=>nodes.map(n=>n.dataset.videoNew)"))

    def library_top(page):
        page.locator("#video-library-title").evaluate("node=>node.scrollIntoView({block:'start',behavior:'instant'})")
        page.evaluate("scrollBy({top:-110,behavior:'instant'})")

    def decode_preview(card):
        card.locator("img").evaluate("image=>{image.loading='eager';return image.decode()}")

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1080}, reduced_motion="reduce")
            page = prepare(context)
            page.goto(origin + "/videos.html", wait_until="domcontentloaded")
            expect_ids(page, expected())
            expect(page.locator("#video-count")).to_have_text(f"Показано {len(VIDEOS)} из {len(VIDEOS)} видео")
            expect(page.locator("#video-screen [data-video-play]")).to_have_attribute("data-video-play", "snag-motion")
            expect(page.locator("#video-channel option")).to_have_count(len(CHANNELS) + 1)
            assert page.locator("#video-screen iframe, #video-screen video").count() == 0
            no_overflow(page)
            checks.append(f"{len(VIDEOS)} cards in publication order; {len(CHANNELS)} channel options; Snag remains the featured poster")

            for video in VIDEOS:
                card = page.locator(f'[data-video-card="{video["id"]}"]')
                date = card.locator(".video-published")
                if builder.publication_time(video.get("publishedAt")):
                    expect(date).to_have_attribute("datetime", video["publishedAt"])
                    assert date.evaluate("node=>node.tagName") == "TIME"
                    expect(date).to_contain_text(".".join(reversed(video["publishedAt"][:10].split("-"))))
                else:
                    expect(date).to_contain_text("публикации не подтверждена")
                    assert date.get_attribute("datetime") is None
                links = card.locator(".video-source a").evaluate_all("nodes=>nodes.map(n=>n.getAttribute('href'))")
                assert links == [video["authorUrl"], video["url"]]
            recent = {v["id"] for v in VIDEOS if (instant := builder.publication_time(v.get("publishedAt")))
                      and timedelta(0) <= NOW - instant < timedelta(days=7)}
            assert new_ids(page) == recent
            checks.append(f"original publication date or an explicit unknown label on every card; {len(recent)} recent badges; original author links preserved")
            for identifier in expected()[:3]:
                decode_preview(page.locator(f'[data-video-card="{identifier}"]'))
            library_top(page)
            page.screenshot(path=str(OUTPUT / "desktop-library.png"))

            for channel in CHANNELS:
                option = page.locator(f'#video-channel option[value="{channel["id"]}"]')
                expect(option).to_have_attribute("data-channel-count", str(channel["count"]))
                page.locator("#video-channel").select_option(channel["id"])
                members = [v for v in VIDEOS if v["id"] in channel["videoIds"]]
                expect_ids(page, expected(members))
                expect(page.locator("#video-channel-source")).to_have_attribute("href", channel["url"])
                if not members:
                    expect(page.locator("#video-empty")).to_be_visible()
                    expect(page.locator("#video-empty-text")).to_contain_text(channel["name"])
                    expect(page.locator("#video-channel-source")).to_be_visible()
            checks.append("every configured/manual channel selectable with its full count; empty channel retains source link and a clear empty state")
            page.locator("#video-channel").select_option("oona-linna-youtube")
            library_top(page)
            page.screenshot(path=str(OUTPUT / "empty-channel.png"))
            page.locator("#video-reset").click()
            expect_ids(page, expected())
            expect(page.locator("#video-channel")).to_have_value("all")
            page.get_by_label("Канал или автор", exact=True).focus()
            page.locator("#video-channel").press("Home")
            page.locator("#video-channel").press("ArrowDown")
            expect(page.locator("#video-channel")).to_have_value(CHANNELS[0]["id"])
            expect_ids(page, expected([v for v in VIDEOS if v["id"] in CHANNELS[0]["videoIds"]]))
            page.locator("#video-channel").select_option("all")
            checks.append("channel picker has an associated accessible label and works with the keyboard")

            page.locator("#video-sort").select_option("oldest")
            expect_ids(page, expected(order="oldest"))
            page.reload(wait_until="domcontentloaded")
            expect_ids(page, expected(order="oldest"))
            expect(page.locator("#video-sort")).to_have_value("oldest")
            page.locator("#video-sort").select_option("newest")
            checks.append("both sorting directions persist across reload and keep unknown dates at the bottom")

            for topic in ("reviews", "tryon", "styling", "choice", "making", "asmr"):
                page.locator(f'[data-video-topic="{topic}"]').click()
                expect_ids(page, expected([v for v in VIDEOS if topic in v["topics"]]))
            page.locator('[data-video-topic="all"]').click()
            for language in ("ru", "en", "none", "original"):
                page.locator("#video-language").select_option(language)
                expect_ids(page, expected([v for v in VIDEOS if v["language"] == language]))
            page.locator("#video-language").select_option("all")
            for provider in ("native", "vimeo", "youtube"):
                page.locator("#video-provider").select_option(provider)
                expect_ids(page, expected([v for v in VIDEOS if v.get("provider", "youtube") == provider]))
            page.locator("#video-provider").select_option("all")
            checks.append("all existing topic, language and player filters still apply in publication order")

            channel = next(c for c in CHANNELS if c["id"] == "dasha-daiz-youtube")
            target = builder.sorted_videos([v for v in VIDEOS if v["id"] in channel["videoIds"]])[0]
            topic, language, provider = target["topics"][0], target["language"], target.get("provider", "youtube")
            page.locator("#video-channel").select_option(channel["id"])
            page.locator("#video-search").fill(target["author"])
            page.locator(f'[data-video-topic="{topic}"]').click()
            page.locator("#video-language").select_option(language)
            page.locator("#video-provider").select_option(provider)
            page.locator("#video-sort").select_option("oldest")
            page.locator(f'[data-video-save="{target["id"]}"]').click()
            page.locator("#video-saved").click()
            expect_ids(page, [target["id"]])
            page.reload(wait_until="domcontentloaded")
            expect_ids(page, [target["id"]])
            query = parse_qs(urlsplit(page.url).query)
            assert query == {"channel": [channel["id"]], "q": [target["author"]], "topic": [topic],
                             "language": [language], "provider": [provider], "sort": ["oldest"], "saved": ["1"]}, query
            expect(page.locator(f'[data-video-save="{target["id"]}"]')).to_have_attribute("aria-pressed", "true")
            checks.append("channel + query + topic + language + provider + order + saved selection all survive reload")

            deep_link = origin + "/videos.html?" + urlencode(dict(video=target["id"], channel=channel["id"], sort="oldest"))
            page.goto(deep_link, wait_until="domcontentloaded")
            expect(page.locator("#video-current-title")).to_have_text(target["title"])
            expect(page.locator("#video-screen [data-video-play]")).to_have_attribute("data-video-play", target["id"])
            expect(page.locator("#video-current-publication time")).to_have_attribute("datetime", target["publishedAt"])
            expect_ids(page, expected([v for v in VIDEOS if v["id"] in channel["videoIds"]], "oldest"))
            before_play = [url for url in blocked if any(host in url for host in ("youtube.com", "player.vimeo.com", "snagtights.com/cdn"))]
            assert not before_play, before_play
            checks.append("existing ?video= deep links keep their selected poster/date, alongside channel/order; no media platform requests before play")

            for width, height in ((768, 1024), (390, 844), (320, 640)):
                mobile = browser.new_context(viewport={"width": width, "height": height}, is_mobile=width < 768,
                                             has_touch=width < 768, reduced_motion="reduce")
                phone = prepare(mobile)
                phone.goto(origin + "/videos.html", wait_until="domcontentloaded")
                no_overflow(phone)
                phone.locator("#video-channel").select_option(channel["id"])
                expect_ids(phone, expected([v for v in VIDEOS if v["id"] in channel["videoIds"]]))
                phone.locator("#video-sort").select_option("oldest")
                expect_ids(phone, expected([v for v in VIDEOS if v["id"] in channel["videoIds"]], "oldest"))
                no_overflow(phone)
                phone.locator(".video-tools").screenshot(path=str(OUTPUT / f"filters-{width}.png"))
                card = phone.locator(f'[data-video-card="{target["id"]}"]')
                decode_preview(card)
                card.screenshot(path=str(OUTPUT / f"dated-card-{width}.png"))
                checks.append(f"{width}px: channel, sort, original date and new badge fit without horizontal overflow")
                mobile.close()

            # Test browser date handling with known fixture instants, not today's feed.
            fixtures = deepcopy(VIDEOS)
            for item in fixtures:
                item.pop("publishedAt", None)
                item["checked"] = NOW.isoformat()
            dates = ["2026-11-17T12:00:00Z", "2026-11-10T12:00:00Z", "2026-11-10T12:00:00.001Z",
                     "2026-11-17T12:00:01Z", "2026-11-17T15:00:00+03:00", "2026-11-16",
                     "2026-02-30", None, "2026-11-17T12:00:00", "1990-01-01", "2026-11-18T01:00:00+14:00"]
            for item, value in zip(fixtures, dates):
                item["publishedAt"] = value
            for zone in ("Asia/Tokyo", "America/Los_Angeles"):
                fixture_context = browser.new_context(timezone_id=zone)
                fixture_page = prepare(fixture_context)
                fixture_context.route("**/data/videos.js*", lambda route: route.fulfill(
                    status=200, content_type="application/javascript", body="window.TONKO_VIDEOS = " + json.dumps(fixtures) + ";"))
                fixture_page.goto(origin + "/videos.html", wait_until="domcontentloaded")
                expect_ids(fixture_page, expected(fixtures))
                assert new_ids(fixture_page) == {fixtures[i]["id"] for i in (0, 2, 4, 5, 10)}
                fixture_page.locator("#video-sort").select_option("oldest")
                expect_ids(fixture_page, expected(fixtures, "oldest"))
                fixture_page.clock.run_for(1)
                assert fixtures[2]["id"] not in new_ids(fixture_page)  # Exactly seven days now.
                fixture_page.clock.run_for(1000)
                assert fixtures[3]["id"] in new_ids(fixture_page)  # Future has become published.
                fixture_page.clock.set_system_time(NOW + timedelta(days=8))
                fixture_page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
                assert not new_ids(fixture_page)
                fixture_page.clock.set_system_time(NOW)
                fixture_page.evaluate("dispatchEvent(new Event('pageshow'))")
                assert new_ids(fixture_page) == {fixtures[i]["id"] for i in (0, 2, 4, 5, 10)}
                checks.append(f"{zone}: timezone offsets, invalid/missing/date-only values, stable ties, exact 7-day expiry, future exclusion, visibility/pageshow refresh")
                fixture_context.close()

            # Check the native player selection only. All stream requests remain blocked.
            page.goto(origin + "/videos.html", wait_until="domcontentloaded")
            page.locator("#video-screen [data-video-play]").click()
            expect(page.locator("#video-screen video")).to_have_attribute("src", next(v["streamUrl"] for v in VIDEOS if v["id"] == "snag-motion"))
            expect(page.locator("#video-stop")).to_be_visible()
            page.locator("#video-stop").click()
            expect(page.locator("#video-screen [data-video-play]")).to_have_attribute("data-video-play", "snag-motion")
            assert page.locator("#video-screen iframe, #video-screen video").count() == 0
            checks.append("Snag starts as a native HTML5 player and closes back to its poster; external stream never fetched")

            assert not errors, errors
            browser.close()
        report = dict(passed=len(checks), checks=checks, catalogue=len(VIDEOS), autoSources=len(SOURCES),
                      channels=len(CHANNELS), emptyChannels=[c["name"] for c in CHANNELS if not c["count"]],
                      recentAtFixedClock=len(recent), clock=NOW.isoformat(), javascriptErrors=errors,
                      externalRequestsBlocked=len(blocked), externalRequestsAllowed=0,
                      playback="UI only; source streams blocked", screenshots=str(OUTPUT))
        (OUTPUT / "qa-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
