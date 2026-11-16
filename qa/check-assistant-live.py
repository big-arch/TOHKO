"""One genuine browser question to the deployed TONKO assistant.

Local site files are served via Playwright routing under the production GitHub
Pages origin. No Supabase/OpenAI response is intercepted or mocked. Desktop and
mobile screenshots show the SAME response, so only one successful AI request is
made. A single 429 retry after the next minute is allowed; other errors stop QA.
"""
from __future__ import annotations

import json
import argparse
import mimetypes
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "tights-guide"
sys.path.insert(0, str(ROOT / ".cache/pw-runtime"))
from playwright.sync_api import sync_playwright, expect

ORIGIN = "https://big-arch.github.io"
BASE = ORIGIN + "/TOHKO/"
OUTPUT = ROOT / ".cache/assistant13"
QUESTION = "Чем отличаются 20 и 40 DEN? Хочу неброский мужской образ с шортами."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", choices=["msedge", "chrome"], default="msedge")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    config = json.loads((SITE / "data/assistant-config.json").read_text(encoding="utf-8"))
    endpoint = config["endpoint"]
    assert config.get("enabled") is True, "Enable only after the owner's live server check"
    assert endpoint == "https://renbakjudvdnkjvjujti.supabase.co/functions/v1/tonko-assistant"
    report = {"checkedAt": datetime.now(timezone.utc).isoformat(), "origin": ORIGIN, "endpoint": endpoint, "browserChannel": args.channel,
              "apiMocked": False, "staticSiteSource": "Local files routed under the production origin", "question": QUESTION, "attempts": [], "passed": False}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1080}, reduced_motion="reduce", service_workers="block")

        def local_static(route):
            parsed = urlsplit(route.request.url)
            assert parsed.netloc == "big-arch.github.io", "This route must never intercept the API"
            name = unquote(parsed.path.removeprefix("/TOHKO/"))
            if name == "__assistant-live-check.html":
                content = (SITE / "index.html").read_text(encoding="utf-8")
                if 'href="assistant.css' not in content:
                    content = content.replace("</head>", '<link rel="stylesheet" href="assistant.css"></head>')
                if 'src="assistant.js' not in content:
                    content = content.replace("</body>", '<script src="assistant.js" defer></script></body>')
                route.fulfill(status=200, body=content, content_type="text/html; charset=utf-8")
                return
            path = (SITE / name).resolve()
            if SITE.resolve() not in path.parents or not path.is_file():
                route.fulfill(status=404, body="Not found")
                return
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            route.fulfill(status=200, body=path.read_bytes(), content_type=content_type)

        # Intentionally only this origin. The Supabase endpoint uses the real network.
        context.route(BASE + "**", local_static)
        # Nonessential font/icon CDNs must not hold DOMContentLoaded when this
        # machine's outbound connection to those unrelated hosts is unavailable.
        for pattern in ["https://fonts.googleapis.com/**", "https://fonts.gstatic.com/**", "https://unpkg.com/**"]:
            context.route(pattern, lambda route: route.abort())
        page = context.new_page()
        page_errors = []
        network_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("requestfailed", lambda request: network_errors.append({"method": request.method, "error": request.failure}) if request.url == endpoint else None)
        try:
            page.goto(BASE + "__assistant-live-check.html", wait_until="domcontentloaded")
            # A free real-network probe prevents a paid question on a blocked path.
            health = page.evaluate("""async config => {
              try { const r = await fetch(config.endpoint, {headers: {apikey: config.publishableKey}, signal: AbortSignal.timeout(12000)});
                return {status: r.status, body: await r.json()}; }
              catch (error) { return {error: String(error)}; }
            }""", config)
            report["health"] = health
            assert health.get("status") == 200 and health.get("body", {}).get("ready") is True, "Real browser health probe failed: " + str(health)
            page.get_by_role("button", name="Спросить ТОНКО").click()
            field = page.locator("#tonko-assistant-input")
            send = page.get_by_role("button", name="Отправить вопрос")
            field.fill(QUESTION)
            expect(send).to_be_enabled()
            for attempt in range(2):
                with page.expect_response(lambda response: response.url == endpoint and response.request.method == "POST", timeout=45000) as waiting:
                    send.click()
                response = waiting.value
                payload = response.json()
                request_origin = response.request.all_headers().get("origin")
                response_origin = response.all_headers().get("access-control-allow-origin")
                report["attempts"].append({"status": response.status, "requestOrigin": request_origin, "allowOrigin": response_origin})
                assert request_origin == ORIGIN and response_origin == ORIGIN, "Production Origin/CORS mismatch"
                if response.status == 429 and attempt == 0:
                    retry = int(payload.get("retryAfter", 60))
                    if retry > 60:
                        raise RuntimeError("Daily limit reached; no additional request was made")
                    wait_seconds = min(60, max(retry + 1, 62 - datetime.now(timezone.utc).second))
                    print(f"Rate limit: waiting {wait_seconds}s before the single retry", flush=True)
                    expect(field).to_have_value(QUESTION)
                    page.wait_for_timeout(wait_seconds * 1000)
                    continue
                assert response.status == 200, f"Live API returned {response.status}: {payload.get('error', 'unknown')}"
                report["response"] = payload
                break
            assert "response" in report
            expect(page.locator(".tonko-assistant-message.is-assistant")).to_have_count(1, timeout=10000)
            answer = page.locator(".tonko-assistant-message.is-assistant .tonko-assistant-text").inner_text()
            assert report["response"]["answer"] in answer
            assert len(report["response"]["answer"]) > 80
            assert "DEN" in answer or "ден" in answer.lower()
            links = page.locator(".tonko-assistant-message.is-assistant .tonko-assistant-sources a").evaluate_all("nodes => nodes.map(a => ({title: a.textContent, href: a.href}))")
            assert links and all(link["href"].startswith(BASE) for link in links)
            report["visibleLinks"] = links
            expect(field).to_be_focused()
            page.locator(".tonko-assistant-conversation").evaluate("node => node.scrollTop = 0")
            page.screenshot(path=str(OUTPUT / "live-answer-desktop.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            panel = page.locator("#tonko-assistant")
            bounds = panel.bounding_box()
            assert bounds["x"] >= 0 and bounds["y"] >= 0 and bounds["x"] + bounds["width"] <= 390 and bounds["y"] + bounds["height"] <= 844
            assert panel.evaluate("node => node.scrollWidth <= node.clientWidth")
            page.locator(".tonko-assistant-conversation").evaluate("node => node.scrollTop = node.scrollHeight")
            page.screenshot(path=str(OUTPUT / "live-answer-mobile.png"))
            expect(page.get_by_role("button", name="Закрыть помощника")).to_be_visible()
            expect(field).to_be_visible()
            page.keyboard.press("Escape")
            expect(panel).not_to_be_visible()
            expect(page.get_by_role("button", name="Спросить ТОНКО")).to_be_focused()
            assert not page_errors, page_errors
            report.update(passed=True, successfulAiRequests=1, screenshots=["live-answer-desktop.png", "live-answer-mobile.png"], pageErrors=page_errors)
        except Exception as error:
            report["failure"] = type(error).__name__ + ": " + str(error)
            page.screenshot(path=str(OUTPUT / "live-failure.png"))
            raise
        finally:
            report["networkErrors"] = network_errors
            (OUTPUT / "live-ui-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            browser.close()
    print(json.dumps({k: report[k] for k in ["checkedAt", "passed", "origin", "apiMocked", "attempts", "successfulAiRequests", "visibleLinks", "screenshots"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
