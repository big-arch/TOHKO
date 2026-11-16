"""Verify AI disclosure in the real UI with an intercepted, non-published fixture."""
from playwright.sync_api import sync_playwright
from pathlib import Path
import json
data=json.loads(Path('tights-guide/data/news.json').read_text(encoding='utf-8'))
record=data['items'][0];record['displayTitle']='Проверка подписи автоматического пересказа'
record['ai']={'model':'gpt-6-luna','generatedAt':'2026-11-16T12:00:00Z','sourceWords':700}
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge');page=browser.new_page()
    page.route('**/data/news.json?*',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(data)))
    page.goto('http://127.0.0.1:4185/',wait_until='networkidle')
    page.locator('#news-new').click()
    assert 'AI-пересказ' in page.locator('.news-item').first.inner_text()
    page.locator('[data-news-id]').first.click()
    assert 'AI-пересказ' in page.locator('.reader-head .news-meta').inner_text()
    assert 'Автоматический пересказ' in page.locator('.reader-credits').inner_text()
    assert 'Рекомендации редакции' not in page.locator('.reader-credits').inner_text()
    browser.close()
print('PASS: AI origin is disclosed on the card and in the reader; fixture was not published.')
