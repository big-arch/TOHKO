"""Read-only release 15 gallery QA; no YouTube/Vimeo playback or AI requests.

Uses an isolated Chrome profile and an automatically selected local HTTP port.
Only the already supplied Snag native player is opened once, then paused/stopped.
Run: C:\\Python313\\python.exe -X utf8 qa/check-video15.py
"""
from __future__ import annotations

import functools
import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "tights-guide"
OUTPUT = ROOT / ".cache/video15-ui"
OUTPUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / ".cache/pw-runtime"))
from playwright.sync_api import expect, sync_playwright

VIDEOS = json.loads((SITE / "data/videos.json").read_text(encoding="utf-8"))
RELEASE14_IDS = {"snag-motion", "snag-details", "CQu5pHHkA0I", "iNjv0X3loYA", "Qg26g0HwX3A", "eXtxikA6iUU", "7jtfXT577FI", "vimeo-1224898418", "2TwccBuvZNQ", "uJCjWLIxweM", "vimeo-1100274499", "vimeo-1102160026", "vimeo-1104089394", "vimeo-1225879573", "vimeo-1241278134", "8ruf9D3Cu4c", "gkbMiMVNwyg", "fW5YzXtsF-A", "xws7aTD4kPU", "eqnpEWFyvHY", "pHSBU0U3940", "efrrmzoIA2E", "d2aX0wwfPJM", "LdfM-MckAf4", "QpApOq2Q0l8", "tSa26mVW5gM"}
NEW = [v for v in VIDEOS if v["id"] not in RELEASE14_IDS]
assert len(VIDEOS) == 52 and len(NEW) == 26


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(SITE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    checks, errors, requests, loaded = [], [], [], []
    native = next(v for v in VIDEOS if v["id"] == "snag-motion")

    def routing(route):
        address = route.request.url
        requests.append(address)
        if address.startswith(origin + "/") or address == native["streamUrl"]:
            route.continue_()
        else:
            route.abort()

    def visible_ids(page):
        return set(page.locator("[data-video-card]:visible").evaluate_all("nodes=>nodes.map(n=>n.dataset.videoCard)"))

    def expect_ids(page, expected):
        expect(page.locator("[data-video-card]:visible")).to_have_count(len(expected))
        assert visible_ids(page) == set(expected)

    def no_overflow(page):
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), page.viewport_size
        offenders = page.locator(".video-tools, .video-card:visible, .video-feature").evaluate_all("nodes=>nodes.filter(n=>n.getBoundingClientRect().right>innerWidth+.5 || n.getBoundingClientRect().left<-.5).map(n=>n.className)")
        assert not offenders, offenders

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1080}, reduced_motion="reduce")
            context.route("**/*", routing)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "/videos.html", wait_until="domcontentloaded")
            expect_ids(page, [v["id"] for v in VIDEOS])
            expect(page.locator("#video-count")).to_have_text("Показано 52 из 52 видео")
            assert page.locator("#video-screen iframe,#video-screen video").count() == 0
            assert not any("youtube.com" in address or "player.vimeo.com" in address for address in requests)
            no_overflow(page)
            page.screenshot(path=str(OUTPUT / "desktop-entry.png"))
            checks.append("52 visible catalogue cards, correct count, no platform player requests before an explicit play click")

            # Load all real local previews through Chrome, including all 26 new files.
            for video in VIDEOS:
                image = page.locator(f'[data-video-card="{video["id"]}"] img')
                image.scroll_into_view_if_needed()
                image.evaluate("e=>e.decode()")
                assert image.evaluate("e=>e.complete && e.naturalWidth>0"), video["id"]
                loaded.append(video["id"])
            checks.append("all 52 real thumbnail files decode in Chrome, including all 26 release 15 additions")

            archives = [v for v in VIDEOS if v.get("archive")]
            assert len(archives) == 16
            for video in archives:
                card = page.locator(f'[data-video-card="{video["id"]}"]')
                expect(card.locator(".video-card-meta")).to_contain_text("Архив")
                date = card.locator(".video-published")
                if video.get("publishedAt"):
                    expect(date).to_have_attribute("datetime", video["publishedAt"][:10])
                    expect(date).to_contain_text("Архив · опубликовано")
                    assert date.evaluate("e=>e.tagName") == "TIME"
                else:
                    expect(date).to_have_text("Архив · дата публикации не подтверждена")
                    assert date.get_attribute("datetime") is None
            page.locator('[data-video-card="G6m9vzvaGoc"]').screenshot(path=str(OUTPUT / "archive-dated-card.png"))
            page.locator('[data-video-card="yqTK5Gs0qmA"]').screenshot(path=str(OUTPUT / "archive-unknown-date-card.png"))
            checks.append("16 archive badges: 11 original dates use time/datetime; 5 unknown dates are explicitly labelled")

            page.locator('[data-video-topic="asmr"]').click()
            asmr = [v for v in VIDEOS if "asmr" in v["topics"]]
            assert len(asmr) == 6
            expect_ids(page, [v["id"] for v in asmr])
            expect(page.locator('[data-video-topic="asmr"]')).to_have_attribute("aria-pressed", "true")
            expect(page.locator("#video-count")).to_have_text("Показано 6 из 52 видео")
            page.locator("#video-library").scroll_into_view_if_needed()
            page.screenshot(path=str(OUTPUT / "desktop-asmr.png"))
            for language in ["ru", "en", "none", "original"]:
                page.locator("#video-language").select_option(language)
                expect_ids(page, [v["id"] for v in asmr if v["language"] == language])
            expect(page.locator("#video-empty")).to_be_visible()
            page.locator("#video-language").select_option("en")
            page.locator("#video-search").fill("WhispersRed")
            expect_ids(page, ["l790AoYh1HE"])
            assert "topic=asmr" in page.url and "language=en" in page.url and "q=WhispersRed" in page.url
            page.reload(wait_until="domcontentloaded")
            expect_ids(page, ["l790AoYh1HE"])
            expect(page.locator("#video-search")).to_have_value("WhispersRed")
            checks.append("ASMR filter returns 6; combined language/search works and survives URL reload")

            page.locator("#video-search").fill("Нет такого выпуска 15-qa")
            expect(page.locator("#video-empty")).to_be_visible()
            page.locator("#video-reset").click()
            expect_ids(page, [v["id"] for v in VIDEOS])
            expect(page.locator("#video-search")).to_be_focused()
            for query in ["макарова", "CALZEDONIA", "керина"]:
                page.locator("#video-search").fill(query)
                expected = [v["id"] for v in VIDEOS if query.lower().replace("ё", "е") in " ".join(str(v.get(k, "")) for k in ["title", "originalTitle", "description", "author"]).lower().replace("ё", "е")]
                expect_ids(page, expected)
            page.locator("#video-search").fill("")
            for language in ["ru", "en", "none", "original"]:
                page.locator("#video-language").select_option(language)
                expect_ids(page, [v["id"] for v in VIDEOS if v["language"] == language])
            page.locator("#video-language").select_option("all")
            for provider in ["native", "vimeo", "youtube"]:
                page.locator("#video-provider").select_option(provider)
                expect_ids(page, [v["id"] for v in VIDEOS if v.get("provider", "youtube") == provider])
            page.locator("#video-provider").select_option("all")
            checks.append("case-insensitive Russian/Latin search, all language/provider filters, empty state and reset")

            # Open only the authorised native player; no claim of real playback quality.
            page.locator('#video-screen [data-video-play="snag-motion"]').click()
            media = page.locator("#video-screen video")
            expect(media).to_be_visible()
            expect(media).to_have_attribute("controls", "")
            expect(media).to_have_attribute("src", native["streamUrl"])
            media.evaluate("e=>e.pause()")
            page.locator("#video-player").screenshot(path=str(OUTPUT / "native-player-open.png"))
            page.locator("#video-stop").click()
            expect(page.locator("#video-screen video,#video-screen iframe")).to_have_count(0)
            expect(page.locator("#video-screen button")).to_be_focused()
            checks.append("one Snag native player opens with controls and stops cleanly; YouTube/Vimeo were not played")

            # Browser-rendered contact sheets are diagnostic pages, not production edits.
            for part in range(2):
                sheet = context.new_page()
                sheet.set_content('<!doctype html><html lang="ru"><meta charset="utf-8"><style>body{margin:24px;background:#faf8f5;color:#302c2b;font:12px Arial}main{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}figure{margin:0}img{width:100%;height:190px;object-fit:contain;background:#231f1d}figcaption{height:52px;padding-top:8px;line-height:1.4}</style><h1>Release 15: новые превью — часть ' + str(part + 1) + '</h1><main></main></html>')
                sheet.evaluate("({videos,origin})=>{for(const v of videos){const f=document.createElement('figure'),i=document.createElement('img'),c=document.createElement('figcaption');i.src=origin+'/'+v.thumbnail;i.alt=v.title;c.textContent=v.id+' · '+v.title;f.append(i,c);document.querySelector('main').append(f)}}", {"videos": NEW[part * 13:(part + 1) * 13], "origin": origin})
                sheet.locator("img").evaluate_all("images=>Promise.all(images.map(i=>i.decode()))")
                sheet.screenshot(path=str(OUTPUT / f"new-previews-{part + 1}.png"), full_page=True)
                sheet.close()

            for width, height in [(390, 844), (320, 640)]:
                mobile = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True, reduced_motion="reduce")
                mobile.route("**/*", routing)
                phone = mobile.new_page()
                phone.on("pageerror", lambda error: errors.append(str(error)))
                phone.goto(origin + "/videos.html", wait_until="domcontentloaded")
                expect_ids(phone, [v["id"] for v in VIDEOS])
                no_overflow(phone)
                phone.locator("#video-library").scroll_into_view_if_needed()
                phone.locator('[data-video-topic="asmr"]').click()
                expect_ids(phone, [v["id"] for v in asmr])
                no_overflow(phone)
                phone.locator(".video-tools").screenshot(path=str(OUTPUT / f"filters-{width}.png"))
                phone.locator("#video-language").select_option("ru")
                expect_ids(phone, ["zu8UTjg3E4U"])
                card = phone.locator('[data-video-card="zu8UTjg3E4U"]')
                card.scroll_into_view_if_needed()
                card.locator("img").evaluate("e=>e.decode()")
                card.screenshot(path=str(OUTPUT / f"asmr-card-{width}.png"))
                no_overflow(phone)
                expect(card.locator(".video-published")).to_have_text("Архив · дата публикации не подтверждена")
                checks.append(f"{width}x{height}: no page/card overflow; filters and Russian ASMR archive card are usable")
                mobile.close()

            assert not errors, errors
            assert not any("youtube.com" in address or "youtube-nocookie.com" in address or "player.vimeo.com" in address for address in requests)
            browser.close()
        report = {"passed": len(checks), "checks": checks, "catalogue": len(VIDEOS), "loadedPreviews": len(loaded),
                  "newPreviews": [v["id"] for v in NEW], "newPreviewsLoaded": len([v for v in NEW if v["id"] in loaded]),
                  "javascriptErrors": errors, "youtubeVimeoPlaybackRequests": 0, "nativePlayer": "opened, paused and stopped; playback not tested",
                  "screenshots": str(OUTPUT), "localServerPort": server.server_port}
        (OUTPUT / "qa-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
