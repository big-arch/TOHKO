"""Release 16 read-only Chrome QA against the actual local catalogue.

No media playback or external service calls. An isolated browser profile and
ephemeral localhost HTTP server are used. All external requests are blocked.
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
OUTPUT = ROOT / "qa/video16-ui"
OUTPUT.mkdir(parents=True, exist_ok=True)
for runtime in (ROOT / ".cache/pw-runtime", Path("C:/Users/Артур/Documents/CODEX_сайт_ТОНКО/.cache/pw-runtime")):
    if runtime.is_dir():
        sys.path.insert(0, str(runtime))
        break
from playwright.sync_api import expect, sync_playwright

VIDEOS = json.loads((SITE / "data/videos.json").read_text("utf-8"))
BASELINE = json.loads((ROOT / "qa/video16-live-baseline.json").read_text("utf-8"))
NEW = [v for v in VIDEOS if v["id"] not in BASELINE["ids"]]
AUTHORS = ["Legslavish", "Poppy Attic", "Dasha Daiz", "FunkyRedFox", "Funhose Studios", "Legs by Layla", "Peyton Kinsly", "OonaLinna"]


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(SITE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    checks, errors, requests, loaded = [], [], [], []
    author_counts = {}
    total = len(VIDEOS)

    def routing(route):
        address = route.request.url
        requests.append(address)
        if address.startswith(origin + "/"):
            route.continue_()
        else:
            route.abort()

    def expect_ids(page, expected):
        expect(page.locator("[data-video-card]:visible")).to_have_count(len(expected))
        actual = page.locator("[data-video-card]:visible").evaluate_all("nodes=>nodes.map(n=>n.dataset.videoCard)")
        assert set(actual) == set(expected), (actual, expected)

    def no_overflow(page):
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), page.viewport_size
        assert not page.locator(".video-tools, .video-card:visible, .video-feature").evaluate_all("nodes=>nodes.filter(n=>n.getBoundingClientRect().right>innerWidth+.5 || n.getBoundingClientRect().left<-.5).map(n=>n.className)")

    def search_ids(query):
        normalized = query.lower().replace("ё", "е")
        return [v["id"] for v in VIDEOS if normalized in " ".join(str(v.get(k, "")) for k in ("title", "originalTitle", "description", "author")).lower().replace("ё", "е")]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1080}, reduced_motion="reduce")
            context.route("**/*", routing)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "/videos.html", wait_until="domcontentloaded")
            expect_ids(page, [v["id"] for v in VIDEOS])
            expect(page.locator("#video-count")).to_have_text(f"Показано {total} из {total} видео")
            assert page.locator("#video-screen iframe,#video-screen video").count() == 0
            no_overflow(page)
            page.screenshot(path=str(OUTPUT / "desktop-entry.png"))
            checks.append(f"{total} cards and correct count at 1440px, no overflow and no media player before play")

            for video in VIDEOS:
                preview = page.locator(f'[data-video-card="{video["id"]}"] img')
                preview.scroll_into_view_if_needed()
                preview.evaluate("e=>e.decode()")
                assert preview.evaluate("e=>e.complete && e.naturalWidth>0"), video["id"]
                loaded.append(video["id"])
            checks.append(f"all {len(loaded)} local previews decode, including {len(NEW)} additions")

            archives = [v for v in VIDEOS if v.get("archive")]
            unknown = [v for v in archives if not v.get("publishedAt")]
            for video in VIDEOS:
                card = page.locator(f'[data-video-card="{video["id"]}"]')
                displayed_date = card.locator(".video-published")
                if video.get("publishedAt"):
                    expect(displayed_date).to_have_attribute("datetime", video["publishedAt"][:10])
                    assert displayed_date.evaluate("e=>e.tagName") == "TIME"
                    if video.get("archive"):
                        expect(displayed_date).to_contain_text("Архив · опубликовано")
                elif video.get("archive"):
                    expect(displayed_date).to_have_text("Архив · дата публикации не подтверждена")
                    assert displayed_date.get_attribute("datetime") is None
                if video.get("archive"):
                    expect(card.locator(".video-card-meta")).to_contain_text("Архив")
            page.locator('[data-video-card="iayHHSfIiKg"]').screenshot(path=str(OUTPUT / "legslavish-archive.png"))
            page.locator('[data-video-card="yqTK5Gs0qmA"]').screenshot(path=str(OUTPUT / "archive-unknown-date.png"))
            checks.append(f"real dates rendered for all dated videos; {len(archives)} archive badges and {len(unknown)} explicit unknown dates")

            for author in AUTHORS:
                page.locator("#video-search").fill(author)
                expected = search_ids(author)
                expect_ids(page, expected)
                author_counts[author] = len(expected)
                no_overflow(page)
                if author == "OonaLinna":
                    assert not expected  # Verified source monitoring, no invented catalogue entry.
                    expect(page.locator("#video-empty")).to_be_visible()
            page.locator("#video-reset").click()
            expect_ids(page, [v["id"] for v in VIDEOS])
            page.locator("#video-search").fill("FunkyRedFox")
            page.locator("#video-language").select_option("ru")
            russian = [v["id"] for v in VIDEOS if v["id"] in search_ids("FunkyRedFox") and v["language"] == "ru"]
            expect_ids(page, russian)
            page.reload(wait_until="domcontentloaded")
            expect_ids(page, russian)
            expect(page.locator("#video-search")).to_have_value("FunkyRedFox")
            checks.append("seven represented authors searchable; OonaLinna correctly has zero cards; combined author/language filters survive reload")
            page.locator("#video-search").fill("")
            page.locator("#video-language").select_option("all")

            for topic in ("reviews", "tryon", "styling", "choice", "making", "asmr"):
                page.locator(f'[data-video-topic="{topic}"]').click()
                expected = [v["id"] for v in VIDEOS if topic in v["topics"]]
                expect_ids(page, expected)
            asmr = [v for v in VIDEOS if "asmr" in v["topics"]]
            expect(page.locator("#video-count")).to_have_text(f"Показано {len(asmr)} из {total} видео")
            page.locator("#video-library").scroll_into_view_if_needed()
            page.screenshot(path=str(OUTPUT / "desktop-asmr.png"))
            page.locator('[data-video-topic="all"]').click()
            for language in ("ru", "en", "none", "original"):
                page.locator("#video-language").select_option(language)
                expect_ids(page, [v["id"] for v in VIDEOS if v["language"] == language])
            page.locator("#video-language").select_option("all")
            for provider in ("native", "vimeo", "youtube"):
                page.locator("#video-provider").select_option(provider)
                expect_ids(page, [v["id"] for v in VIDEOS if v.get("provider", "youtube") == provider])
            page.locator("#video-provider").select_option("all")
            checks.append(f"all topic/language/provider filters work; textile ASMR has {len(asmr)} records")

            for video in NEW:
                source = page.locator(f'[data-video-card="{video["id"]}"] .video-source')
                links = source.locator("a").evaluate_all("nodes=>nodes.map(n=>n.getAttribute('href'))")
                assert links == [video["authorUrl"], video["url"]], video["id"]
            saved_id = "O3-nEUl9bFs"
            page.locator(f'[data-video-save="{saved_id}"]').click()
            page.locator("#video-saved").click()
            expect_ids(page, [saved_id])
            page.reload(wait_until="domcontentloaded")
            expect_ids(page, [saved_id])
            page.locator("#video-saved").click()
            checks.append("all new cards link to their verified author and original; saved selection persists on reload")

            # Browser-generated contact sheets are QA artefacts, not site edits.
            for start in range(0, len(NEW), 12):
                sheet = context.new_page()
                sheet.set_content('<!doctype html><html lang="ru"><meta charset="utf-8"><style>body{margin:24px;background:#faf8f5;color:#302c2b;font:12px Arial}main{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}figure{margin:0}img{width:100%;height:190px;object-fit:contain;background:#231f1d}figcaption{height:56px;padding-top:8px;line-height:1.4}</style><h1>Release 16: добавленные превью</h1><main></main></html>')
                sheet.evaluate("({videos,origin})=>{for(const v of videos){const f=document.createElement('figure'),i=document.createElement('img'),c=document.createElement('figcaption');i.src=origin+'/'+v.thumbnail;i.alt=v.title;c.textContent=v.id+' · '+v.title;f.append(i,c);document.querySelector('main').append(f)}}", {"videos": NEW[start:start+12], "origin": origin})
                sheet.locator("img").evaluate_all("images=>Promise.all(images.map(i=>i.decode()))")
                sheet.screenshot(path=str(OUTPUT / f"new-previews-{start//12+1}.png"), full_page=True)
                sheet.close()

            for width, height in ((390, 844), (320, 640)):
                mobile = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True, reduced_motion="reduce")
                mobile.route("**/*", routing)
                phone = mobile.new_page()
                phone.on("pageerror", lambda error: errors.append(str(error)))
                phone.goto(origin + "/videos.html", wait_until="domcontentloaded")
                expect_ids(phone, [v["id"] for v in VIDEOS])
                no_overflow(phone)
                phone.locator("#video-library").scroll_into_view_if_needed()
                phone.locator("#video-search").fill("Dasha Daiz")
                expect_ids(phone, search_ids("Dasha Daiz"))
                no_overflow(phone)
                phone.locator(".video-tools").screenshot(path=str(OUTPUT / f"filters-{width}.png"))
                card = phone.locator('[data-video-card="O3-nEUl9bFs"]')
                card.scroll_into_view_if_needed()
                card.locator("img").evaluate("e=>e.decode()")
                card.screenshot(path=str(OUTPUT / f"new-card-{width}.png"))
                expect(card.locator(".video-published")).to_have_attribute("datetime", "2026-11-15")
                phone.locator("#video-search").fill("")
                phone.locator('[data-video-topic="asmr"]').click()
                phone.locator("#video-language").select_option("ru")
                expect_ids(phone, [v["id"] for v in asmr if v["language"] == "ru"])
                no_overflow(phone)
                checks.append(f"{width}x{height}: all cards, new-author search, dates and ASMR/language filters without overflow")
                mobile.close()

            assert not errors, errors
            platform_requests = [u for u in requests if any(h in u for h in ("youtube.com", "youtube-nocookie.com", "player.vimeo.com"))]
            assert not platform_requests, platform_requests
            browser.close()
        report = dict(passed=len(checks), checks=checks, catalogue=total, loadedPreviews=len(loaded),
            newPreviews=len(NEW), authorSearchCounts=author_counts, javascriptErrors=errors,
            youtubeVimeoRequestsBeforePlay=len(platform_requests), playback="not requested or tested",
            screenshots=str(OUTPUT), localServerPort=server.server_port)
        (OUTPUT / "qa-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
