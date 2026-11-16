"""Offline photo/chat UI checks against real local pages and a mocked API.

No Supabase/OpenAI request, browser storage from the user or production changes.
Run with C:\\Python313\\python.exe -X utf8 qa/check-assistant14.py.
"""
from __future__ import annotations

import copy
import functools
import importlib.util
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("assistant13_qa", ROOT / "qa/check-assistant.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
from playwright.sync_api import sync_playwright, expect

OUTPUT = ROOT / ".cache/assistant14"
OUTPUT.mkdir(parents=True, exist_ok=True)
STATE = base.STATE
DATA = json.loads((base.SITE / "data/assistant-knowledge.json").read_text(encoding="utf-8"))
PHOTOS = [p for p in DATA["photos"] if p["id"] in ["gallery-adrian-city", "gallery-adrian-pattern", "style-glamory-classic20-black"]]
assert len(PHOTOS) == 3


class Handler(base.Handler):
    def do_POST(self):
        mode = STATE["mode"]
        if mode not in ["photos", "badphotos", "broken", "empty"]:
            return super().do_POST()
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        STATE["requests"].append({"body": data, "apikey": self.headers.get("apikey")})
        photos = copy.deepcopy(PHOTOS)
        if mode == "badphotos":
            photos[0]["src"] = "https://evil.example.org/track.jpg"
            photos[1]["source"] = "javascript:alert(1)"
            photos[2]["caption"] = '<img src=x onerror="window.injected=true">'
        if mode == "broken":
            photos = [photos[0]]
            photos[0]["src"] = "assets/editorial/assistant-qa-missing.jpg"
            photos[0]["thumb"] = "assets/editorial/assistant-qa-missing-thumb.jpg"
        if mode == "empty":
            photos = []
        self.send_json({"answer": "Вот три мужских образа: с пиджаком, шортами и выразительным рисунком. Плотность указана там, где её подтверждает источник." if mode != "empty" else "Парных фото с подтверждёнными 20 DEN в этой подборке нет. Могу показать парные образы без точной плотности.",
                        "nextQuestion": None, "sources": [{"title": "Мужские образы", "href": "men.html"}], "photos": photos})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(base.SITE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    url = origin + "/__assistant-preview.html"
    checks, errors = [], []
    STATE.update(enabled=True, mode="photos", requests=[])
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1080}, reduced_motion="reduce")
            context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(origin + "/") else route.abort())
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url, wait_until="domcontentloaded")
            page.get_by_role("button", name="Спросить ТОНКО").click()
            field = page.locator("#tonko-assistant-input")
            send = page.get_by_role("button", name="Отправить вопрос")
            expect(field).to_be_focused()
            field.fill("Покажи фото мужских образов")
            send.click()
            cards = page.locator(".tonko-assistant-photo")
            expect(cards).to_have_count(3)
            expect(page.locator(".tonko-assistant-photo-detail").first).to_have_text("DEN не указан")
            expect(page.locator(".tonko-assistant-photo .tonko-assistant-photo-detail").last).to_have_text("20 DEN · по источнику")
            assert all(img.evaluate("e=>e.complete && e.naturalWidth > 0") for img in page.locator(".tonko-assistant-photo img").all())
            assert STATE["requests"][-1]["body"]["history"] == []
            assert STATE["requests"][-1]["apikey"] == base.PUBLIC_KEY
            page.screenshot(path=str(OUTPUT / "photos-desktop.png"))
            checks.append("3 real local photos, source links, explicit unknown DEN and public apikey")

            trigger = page.locator(".tonko-assistant-photo-open").first
            trigger.click()
            gallery = page.locator(".tonko-assistant-gallery")
            expect(gallery).to_be_visible()
            expect(page.get_by_role("button", name="Закрыть фото", exact=True)).to_be_focused()
            expect(gallery.locator("img")).to_have_attribute("src", origin + "/" + PHOTOS[0]["src"])
            source = gallery.locator("figcaption a")
            assert source.get_attribute("href") == PHOTOS[0]["source"]
            assert "noopener" in source.get_attribute("rel")
            page.get_by_role("button", name="Следующее фото", exact=True).click()
            expect(gallery.locator("[role=status]")).to_have_text("2 / 3")
            page.keyboard.press("ArrowLeft")
            expect(gallery.locator("[role=status]")).to_have_text("1 / 3")
            for _ in range(8):
                page.keyboard.press("Tab")
                assert page.evaluate("Boolean(document.activeElement.closest('.tonko-assistant-gallery'))")
            page.screenshot(path=str(OUTPUT / "gallery-desktop.png"))
            page.keyboard.press("Escape")
            expect(gallery).not_to_be_visible()
            expect(trigger).to_be_focused()
            expect(page.locator("#tonko-assistant")).to_be_visible()
            checks.append("zoom, previous/next/arrow, source attribution, focus trap and Escape returns to card")

            page.reload(wait_until="domcontentloaded")
            page.get_by_role("button", name="Спросить ТОНКО").click()
            expect(page.locator(".tonko-assistant-photo")).to_have_count(3)
            field.fill("А какой DEN на втором фото?")
            send.click()
            expect(page.locator(".tonko-assistant-message.is-assistant")).to_have_count(2)
            outgoing = STATE["requests"][-1]["body"]["history"]
            assert outgoing[0]["content"] == "Покажи фото мужских образов"
            assert "ID:" + PHOTOS[1]["id"] in outgoing[1]["content"]
            assert "DEN не указан" in outgoing[1]["content"]
            assert "https://" not in outgoing[1]["content"]
            checks.append("photos survive reload; follow-up history has ordered IDs and verified/unknown metadata without URLs")

            page.get_by_role("button", name="Очистить переписку в этой вкладке").click()
            STATE["mode"] = "badphotos"
            field.fill("Проверка недоверенных фотографий")
            send.click()
            expect(page.locator(".tonko-assistant-photo")).to_have_count(1)
            page.locator(".tonko-assistant-photo-open").click()
            expect(gallery.locator("figcaption")).to_contain_text('<img src=x onerror="window.injected=true">')
            assert gallery.locator("figcaption img").count() == 0
            assert page.evaluate("window.injected === undefined")
            assert page.locator('img[src*="evil.example"]').count() == 0
            page.keyboard.press("Escape")
            checks.append("external image and javascript source rejected; caption markup stays inert text")

            page.get_by_role("button", name="Очистить переписку в этой вкладке").click()
            STATE["mode"] = "broken"
            field.fill("Покажи фото с ошибкой загрузки")
            send.click()
            expect(page.locator(".tonko-assistant-photo-error").first).to_be_visible()
            page.locator(".tonko-assistant-photo-open").click()
            expect(gallery.locator(".tonko-assistant-photo-error")).to_be_visible()
            expect(gallery.locator("figcaption a")).to_be_visible()
            expect(page.get_by_role("button", name="Следующее фото", exact=True)).to_be_disabled()
            page.screenshot(path=str(OUTPUT / "photo-load-error.png"))
            page.keyboard.press("Escape")
            checks.append("missing thumbnail/full image has readable fallback, usable source and close control")

            page.get_by_role("button", name="Очистить переписку в этой вкладке").click()
            STATE["mode"] = "empty"
            field.fill("Покажи парные фото 20 DEN")
            send.click()
            expect(page.locator(".tonko-assistant-message.is-assistant")).to_contain_text("нет")
            expect(page.locator(".tonko-assistant-photo")).to_have_count(0)
            STATE["mode"] = "limit"
            field.fill("Ещё фото")
            send.click()
            expect(page.locator(".tonko-assistant-notice")).to_contain_text("слишком много вопросов")
            expect(field).to_have_value("Ещё фото")
            expect(send).to_be_enabled()
            checks.append("no-match response has no fake photo; 429 preserves recoverable question")

            STATE["mode"] = "photos"
            for width, height in [(390, 844), (320, 640), (844, 390)]:
                mobile = browser.new_context(viewport={"width": width, "height": height}, is_mobile=True, has_touch=True, device_scale_factor=1, reduced_motion="reduce")
                mobile.route("**/*", lambda route: route.continue_() if route.request.url.startswith(origin + "/") else route.abort())
                phone = mobile.new_page()
                phone.on("pageerror", lambda error: errors.append(str(error)))
                phone.goto(url, wait_until="domcontentloaded")
                phone.get_by_role("button", name="Спросить ТОНКО").click()
                phone.get_by_role("button", name="Фото мужских образов", exact=True).click()
                expect(phone.locator(".tonko-assistant-photo")).to_have_count(3)
                panel = phone.locator("#tonko-assistant")
                box = panel.bounding_box()
                assert box["x"] >= 0 and box["y"] >= 0 and box["x"] + box["width"] <= width and box["y"] + box["height"] <= height
                assert panel.evaluate("e=>e.scrollWidth <= e.clientWidth")
                expect(phone.locator("#tonko-assistant-input")).to_be_visible()
                phone.screenshot(path=str(OUTPUT / f"photos-{width}x{height}.png"))
                phone.locator(".tonko-assistant-photo-open").first.click()
                viewer = phone.locator(".tonko-assistant-gallery")
                expect(viewer).to_be_visible()
                assert viewer.evaluate("e=>e.scrollWidth <= e.clientWidth")
                expect(phone.get_by_role("button", name="Закрыть фото", exact=True)).to_be_visible()
                expect(phone.get_by_role("button", name="Следующее фото", exact=True)).to_be_visible()
                phone.screenshot(path=str(OUTPUT / f"gallery-{width}x{height}.png"))
                phone.get_by_role("button", name="Закрыть фото", exact=True).click()
                expect(viewer).not_to_be_visible()
                checks.append(f"{width}x{height}: photo strip, composer, bounded gallery, reachable navigation and close")
                mobile.close()
            assert not errors, errors
            browser.close()
        report = {"passed": len(checks), "checks": checks, "browser": "Chrome via Playwright (isolated headless profile)", "real_ai_requests": 0, "screenshots": str(OUTPUT)}
        (OUTPUT / "qa-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
