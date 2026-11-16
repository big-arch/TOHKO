"""Player UX contract. --live also checks real anonymous media without stubs."""
import argparse
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true')
args = parser.parse_args()
BASE = os.environ.get('TONKO_TEST_URL', 'http://127.0.0.1:4185/')
OUT = Path('qa')

with sync_playwright() as pw:
    browser = pw.chromium.launch(channel='chrome')
    context = browser.new_context(viewport={'width':1440,'height':1000})
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    requests = []
    page.on('request', lambda req: requests.append(req.url))
    page.goto(BASE+'videos.html?video=8ruf9D3Cu4c', wait_until='domcontentloaded')
    assert page.locator('#video-screen iframe,#video-screen video').count() == 0
    assert not [u for u in requests if any(h in u for h in ['youtube.com','youtube-nocookie.com','player.vimeo.com'])], requests
    assert page.locator('.video-account-settings,#video-youtube-mode,#youtube-use-account,#youtube-reconnect').count() == 0
    assert not page.locator('#video-youtube-help').is_visible()
    assert page.locator('[data-video-card]').count() == page.evaluate('TONKO_VIDEOS.length')
    assert page.locator('.video-published').count() == page.evaluate('TONKO_VIDEOS.filter(v=>v.publishedAt).length')
    # Failure callbacks are deterministic UI coverage, not proof of playback.
    page.route('https://www.youtube.com/**', lambda route: route.fulfill(status=200, content_type='text/html', body='<html><body>Player test</body></html>'))
    page.evaluate('''() => {window.YT={Player:function(frame,options){
      const target={destroy(){},getCurrentTime(){return 0},getDuration(){return 60},getPlayerState(){return 1},seekTo(){}};
      window.testYouTubeEvents=options.events;
      setTimeout(()=>options.events.onReady({target}),0);return target;
    }};}''')
    # A stale preference from the former UI must not require a setup click.
    page.evaluate("localStorage.setItem('tonko-youtube-mode','private')")
    page.locator('.video-start').click()
    frame = page.locator('#tonko-video-player')
    src = frame.get_attribute('src')
    assert src.startswith('https://www.youtube.com/embed/8ruf9D3Cu4c?'), src
    assert 'autoplay=1' in src and 'mute=' not in src and 'muted=' not in src
    assert frame.get_attribute('referrerpolicy') == 'strict-origin-when-cross-origin'
    assert not page.locator('#video-youtube-help').is_visible()
    page.evaluate('testYouTubeEvents.onError({data:101})')
    assert page.locator('#video-youtube-help').is_visible()
    assert page.locator('#video-retry').is_visible()
    assert page.locator('#video-alternative').is_visible()
    assert 'не бот' in page.locator('#video-youtube-help').inner_text()
    page.screenshot(path=str(OUT/'video14-error-desktop.png'))
    page.locator('#video-stop').click()
    assert page.locator('#tonko-video-player').count() == 0
    assert not page.locator('#video-youtube-help').is_visible()
    page.locator('[data-video-save="8ruf9D3Cu4c"]').click()
    page.locator('#video-saved').click()
    assert page.locator('[data-video-card]:visible').count() == 1
    page.locator('#video-reset').click() if page.locator('#video-reset').is_visible() else page.locator('#video-saved').click()
    for width in [390, 320]:
        page.set_viewport_size({'width':width, 'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.locator('#video-provider').select_option('vimeo')
        assert page.locator('[data-video-card]:visible').count() == page.evaluate('TONKO_VIDEOS.filter(v=>v.provider==="vimeo").length')
        if width == 390:
            page.screenshot(path=str(OUT/'video14-mobile.png'), full_page=True)
    assert not errors, errors
    context.close()
    print('PASS UI: no account setup, no platform request before click, official automatic host, error-only help, stop, saved videos, dates, filters, mobile 390/320')

    if args.live:
        # A fresh context has no YouTube/Google account or saved cookies.
        live = browser.new_context(viewport={'width':1365, 'height':900})
        page = live.new_page()
        results = []
        for ident in ['snag-motion', 'vimeo-1224898418', 'CQu5pHHkA0I']:
            page.goto(BASE+'videos.html?video='+ident, wait_until='domcontentloaded')
            page.locator('.video-start').click()
            state = {}
            for _ in range(45 if ident.startswith('snag-') else 24):
                page.wait_for_timeout(1000)
                media_frame = page if ident.startswith('snag-') else next((f for f in page.frames if ('player.vimeo.com/video/' in f.url or 'youtube.com/embed/' in f.url)), None)
                if not media_frame:
                    continue
                try:
                    states = media_frame.locator('video').evaluate_all('(vs)=>vs.map(v=>({time:v.currentTime,paused:v.paused,ready:v.readyState,duration:Number.isFinite(v.duration)?v.duration:null,error:v.error?.code,muted:v.muted}))')
                    state = states[0] if states else {}
                    if state.get('time',0) > 3 and not state.get('paused',True):
                        break
                    text = media_frame.locator('body').inner_text(timeout=1500)
                    if any(message in text for message in ['не бот', 'not a bot', "couldn't verify the security", 'Access to this content has been restricted']):
                        state['platformMessage'] = text[:400]
                        break
                except Exception:
                    continue
            played = state.get('time',0)>3 and not state.get('paused',True)
            if played:
                before = state['time']
                page.wait_for_timeout(1500)
                after = media_frame.locator('video').first.evaluate('(v)=>v.currentTime')
                assert after > before + 0.5, (ident, before, after)
                state['after'] = after
            outcome = 'played' if played else 'platform_restricted' if state.get('platformMessage') else 'unavailable'
            results.append({'id':ident, 'outcome':outcome, **state})
            page.screenshot(path=str(OUT/('video14-live-'+ident+'.png')))
            page.locator('#video-stop').click()
            assert page.locator('#video-screen iframe,#video-screen video').count()==0
        (OUT/'video14-live.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(results, ensure_ascii=False))
        live.close()
        assert results[0]['outcome']=='played', results[0]
        # Keep blocked playback visible as a failing live check, while still
        # recording all providers. The deterministic UI check above is separate.
        if any(r['outcome']!='played' for r in results):
            raise SystemExit('LIVE LIMITED: platform restrictions recorded in qa/video14-live.json; no bypass attempted')
    browser.close()
