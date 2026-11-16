"""Offline browser QA. In-memory HTML injection and a local mock HTTP server.

Does not alter production HTML/config or call Supabase/OpenAI. Uses the isolated
Playwright runtime at .cache/pw-runtime. Screenshots: .cache/assistant13/.
"""
from __future__ import annotations

import functools
import json
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "tights-guide"
sys.path.insert(0, str(ROOT / ".cache/pw-runtime"))
from playwright.sync_api import sync_playwright, expect

OUTPUT = ROOT / ".cache/assistant13"
OUTPUT.mkdir(parents=True, exist_ok=True)
STATE = {"enabled": True, "mode": "ok", "requests": []}
PUBLIC_KEY = "sb_publishable_offline_test"


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_GET(self):
        if self.path.startswith("/data/assistant-config.json"):
            self.send_json({"enabled": STATE["enabled"], "endpoint": f"http://127.0.0.1:{self.server.server_port}/mock-assistant", "publishableKey": PUBLIC_KEY})
            return
        if self.path.startswith("/__assistant-preview.html"):
            text = (SITE / "index.html").read_text(encoding="utf-8")
            # Other workers may have integrated the widget by the time QA runs.
            if 'href="assistant.css' not in text:
                text = text.replace("</head>", '<link rel="stylesheet" href="assistant.css"></head>')
            if 'src="assistant.js' not in text:
                text = text.replace("</body>", '<script src="assistant.js" defer></script></body>')
            body = text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/mock-assistant":
            self.send_error(404)
            return
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        STATE["requests"].append({"body": data, "apikey": self.headers.get("apikey")})
        mode = STATE["mode"]
        if mode == "slow":
            time.sleep(1.2)
        if mode == "limit":
            self.send_json({"error": "rate_limited", "retryAfter": 60}, 429)
            return
        if mode == "unavailable":
            self.send_json({"error": "not_configured"}, 503)
            return
        self.send_json({
            "answer": "20 DEN обычно выбирают ради более лёгкого визуального эффекта. Само число описывает нить: прозрачность также зависит от вязки, цвета и посадки." if mode != "unsafe" else '<img src=x onerror="window.unsafe=true"> — это текст, не разметка.',
            "nextQuestion": "Вам нужна прозрачная пара или более плотный вид?",
            "sources": [{"id": "guide-den", "title": "Сравнить DEN", "href": "guide.html#den-lab"},
                        {"id": "bad", "title": "Внешняя подмена", "href": "javascript:alert(1)"}],
        })


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(SITE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/__assistant-preview.html"
    checks = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(f"http://127.0.0.1:{server.server_port}/") else route.abort())
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url, wait_until="domcontentloaded")
            launcher = page.get_by_role("button", name="Спросить ТОНКО")
            launcher.click()
            panel = page.locator("#tonko-assistant")
            field = page.locator("#tonko-assistant-input")
            send = page.get_by_role("button", name="Отправить вопрос")
            expect(panel).to_be_visible()
            expect(field).to_be_focused()
            page.screenshot(path=str(OUTPUT / "welcome-desktop.png"))
            field.fill("Чем отличаются 20 и 40 DEN?")
            expect(send).to_be_enabled()
            field.press("Enter")
            expect(page.locator(".tonko-assistant-message.is-assistant")).to_have_count(1)
            expect(page.get_by_role("link", name="Сравнить DEN →")).to_have_attribute("href", f"http://127.0.0.1:{server.server_port}/guide.html#den-lab")
            expect(page.get_by_role("link", name="Внешняя подмена")).to_have_count(0)
            assert STATE["requests"][0]["apikey"] == PUBLIC_KEY
            assert STATE["requests"][0]["body"]["history"] == []
            expect(field).to_be_focused()
            checks.append("send + public apikey + grounded source link + external URL rejection")
            page.screenshot(path=str(OUTPUT / "answer-desktop.png"))

            page.reload(wait_until="domcontentloaded")
            launcher.click()
            expect(page.locator(".tonko-assistant-message")).to_have_count(2)
            field.focus()
            for _ in range(12):
                page.keyboard.press("Tab")
                assert page.evaluate("Boolean(document.activeElement.closest('#tonko-assistant'))")
            page.keyboard.press("Escape")
            expect(panel).not_to_be_visible()
            expect(launcher).to_be_focused()
            checks.append("sessionStorage reload + focus trap + Escape focus return")

            launcher.click()
            STATE["mode"] = "slow"
            field.fill("Вопрос, который я остановлю")
            send.click()
            expect(page.get_by_role("button", name="Остановить")).to_be_visible()
            expect(send).to_be_disabled()
            page.get_by_role("button", name="Остановить").click()
            expect(field).to_be_editable()
            page.wait_for_timeout(1400)
            expect(page.locator(".tonko-assistant-message.is-assistant")).to_have_count(1)
            checks.append("abort suppresses late answer and duplicate send")

            STATE["mode"] = "limit"
            field.fill("Новый вопрос")
            send.click()
            expect(page.locator(".tonko-assistant-notice")).to_contain_text("слишком много вопросов")
            expect(field).to_have_value("Новый вопрос")
            expect(send).to_be_enabled()
            checks.append("429 shows recoverable error and preserves question")

            STATE["mode"] = "unsafe"
            field.fill("Проверка текстового ответа")
            send.click()
            expect(page.locator(".tonko-assistant-message.is-assistant")).to_have_count(2)
            expect(page.locator(".tonko-assistant-message img")).to_have_count(0)
            assert page.evaluate("window.unsafe === undefined")
            checks.append("provider text cannot inject HTML")
            page.get_by_role("button", name="Очистить переписку в этой вкладке").click()
            expect(page.locator(".tonko-assistant-message")).to_have_count(0)
            assert page.evaluate("sessionStorage.getItem('tonko.assistant.v1')") is None
            checks.append("clear removes storage and conversation")

            STATE["enabled"] = False
            page.reload(wait_until="domcontentloaded")
            launcher.click()
            field.fill("Тест без подключённого сервера")
            expect(send).to_be_disabled()
            expect(page.locator(".tonko-assistant-notice")).to_contain_text("ещё подключается")
            expect(page.get_by_role("link", name="Упаковки →", exact=True)).to_be_visible()
            checks.append("unconfigured mode has no fake AI response")

            STATE["enabled"] = True
            STATE["mode"] = "ok"
            mobile = browser.new_context(viewport={"width": 320, "height": 640}, is_mobile=True, has_touch=True, device_scale_factor=1, reduced_motion="reduce")
            mobile.route("**/*", lambda route: route.continue_() if route.request.url.startswith(f"http://127.0.0.1:{server.server_port}/") else route.abort())
            phone = mobile.new_page()
            phone.goto(url, wait_until="domcontentloaded")
            phone.get_by_role("button", name="Спросить ТОНКО").click()
            mobile_panel = phone.locator("#tonko-assistant")
            bounds = mobile_panel.bounding_box()
            assert bounds["x"] >= 0 and bounds["y"] >= 0 and bounds["x"] + bounds["width"] <= 320 and bounds["y"] + bounds["height"] <= 640
            assert phone.locator("#tonko-assistant").evaluate("e => e.scrollWidth <= e.clientWidth")
            expect(phone.locator("#tonko-assistant-input")).to_be_visible()
            expect(phone.get_by_role("button", name="Закрыть помощника")).to_be_visible()
            phone.screenshot(path=str(OUTPUT / "welcome-mobile-320.png"))
            phone.get_by_role("button", name="20 или 40 DEN?").click()
            expect(phone.locator(".tonko-assistant-message.is-assistant")).to_have_count(1)
            phone.screenshot(path=str(OUTPUT / "answer-mobile-320.png"))
            checks.append("320px mobile layout, visible composer, quick question")
            assert not errors, errors
            browser.close()
        report = {"passed": len(checks), "checks": checks, "screenshots": str(OUTPUT), "real_ai_requests": 0}
        (OUTPUT / "qa-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
