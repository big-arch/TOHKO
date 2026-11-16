"""Real native Snag media test, no platform stubs; needs network access."""
from playwright.sync_api import sync_playwright
import json
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge')
    page=browser.new_page(viewport={'width':1365,'height':900})
    page.goto('http://127.0.0.1:4185/videos.html',wait_until='networkidle')
    page.locator('.video-start').click()
    video=page.locator('#video-screen > video')
    try:video.wait_for(state='attached',timeout=25000)
    except Exception:
        page.screenshot(path='qa/media8-playback-error.png')
        print('Frames:',[(f.url,f.locator('body').inner_text(timeout=2000)[:600]) for f in page.frames])
        raise
    # The site initiates playback after a user click; observe the actual media element.
    for n in range(12):
        state=video.evaluate('(v)=>({time:v.currentTime,paused:v.paused,ready:v.readyState,duration:v.duration,error:v.error?.code})')
        if state['time']>5 and not state['paused']:break
        page.wait_for_timeout(1500)
    assert state['time']>5 and not state['paused'],state
    before=state['time'];page.wait_for_timeout(2000)
    after=video.evaluate('(v)=>v.currentTime');assert after>before+1,(before,after)
    page.screenshot(path='qa/media8-native-playing.png')
    page.locator('#video-stop').click();assert page.locator('#video-screen > video').count()==0
    page.reload(wait_until='networkidle');label=page.locator('.video-start').inner_text()
    assert 'Продолжить' in label,label
    page.locator('.video-start').click();video=page.locator('#video-screen > video')
    video.wait_for(state='attached',timeout=30000)
    for n in range(10):
        resumed=video.evaluate('(v)=>v.currentTime')
        if resumed>=before-1:break
        page.wait_for_timeout(1000)
    assert resumed>=before-1,(before,resumed)
    print(json.dumps(dict(result='PASS',before=before,after=after,resumed=resumed,label=label),ensure_ascii=False))
    browser.close()
