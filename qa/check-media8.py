"""Local browser smoke test. Uses real pages; media availability checked separately."""
from playwright.sync_api import sync_playwright
from pathlib import Path
import json
BASE='http://127.0.0.1:4185/'
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge')
    context=browser.new_context(viewport={'width':1440,'height':1000})
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE,wait_until='networkidle')
    link=page.locator('#news-list [data-news-id]').first
    title=link.inner_text();link.click()
    assert page.locator('dialog[open] h2').inner_text()==title
    assert page.url.startswith(BASE) and '?news=' in page.url
    page.screenshot(path='qa/media8-reader-desktop.png')
    page.go_back();assert page.locator('dialog[open]').count()==0
    page.go_forward();assert page.locator('dialog[open]').count()==1
    page.keyboard.press('Escape');assert page.locator('dialog[open]').count()==0
    assert page.evaluate('document.activeElement.matches("[data-news-id]")')
    link.click();deep=page.url;page.reload(wait_until='networkidle');assert page.locator('dialog[open]').count()==1
    page.locator('.reader-close').click()
    page.goto(BASE+'lookbook.html?filter=packaging',wait_until='networkidle')
    assert page.locator('[data-gallery-filter="packaging"][aria-pressed="true"]').count()==1
    assert page.get_by_text('OMSA · Attiva 40',exact=True).count()>=1
    page.goto(BASE+'videos.html',wait_until='networkidle')
    assert page.locator('[data-video-card]').count()==18
    assert page.locator('iframe').count()==0
    page.locator('.video-account-settings summary').click()
    page.locator('#video-youtube-mode').select_option('standard')
    page.reload(wait_until='networkidle');assert page.locator('#video-youtube-mode').input_value()=='standard'
    # Seed only progress to exercise the complete page resume UI without a video platform mock.
    page.evaluate("localStorage.setItem('tonko-video-progress-v1',JSON.stringify({'snag-motion':{seconds:5,duration:19.904,at:Date.now()}}))")
    page.reload(wait_until='networkidle');assert '0:05' in page.locator('.video-start').inner_text()
    page.locator('#video-provider').select_option('vimeo');assert page.locator('[data-video-card]:visible').count()==5
    for width in [390,320]:
        page.set_viewport_size({'width':width,'height':844})
        page.goto(deep,wait_until='networkidle')
        assert page.locator('dialog[open]').count()==1
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert page.locator('.news-reader').evaluate('(n)=>n.scrollWidth<=n.clientWidth+1')
        if width==390:page.screenshot(path='qa/media8-reader-mobile.png')
        page.keyboard.press('Escape')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
print('PASS: in-site reader, Back/Forward, Escape/focus, direct link/reload, packaging, 18 videos, player preference, resume UI, mobile 390/320, no JS errors')
