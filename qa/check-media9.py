"""Browser acceptance checks for the expanded news reader and packaging archive."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE=os.environ.get('TONKO_TEST_URL','http://127.0.0.1:4185/')
OUT=Path('qa');OUT.mkdir(exist_ok=True)
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='msedge')
    context=browser.new_context(viewport={'width':1440,'height':1000})
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE,wait_until='networkidle')
    article=page.locator('[data-news-id="a3973b36c3edd608"]');article.click()
    assert page.locator('.news-reader[open]').count()==1
    assert page.locator('.reader-copy section').count()==3
    assert len(page.locator('.reader-article').inner_text())>2500
    assert page.locator('.reader-visual img').get_attribute('src').endswith('pkg-a003df0fca.webp')
    page.wait_for_function('document.querySelector(".reader-visual img")?.naturalWidth>0')
    assert 'ss-clara' not in page.locator('.reader-body').inner_html()
    page.screenshot(path=str(OUT/'media9-news-desktop.png'))
    page.go_back();assert page.locator('.news-reader[open]').count()==0
    page.go_forward();assert page.locator('.news-reader[open]').count()==1
    page.keyboard.press('Escape');assert page.locator('.news-reader[open]').count()==0
    assert page.evaluate('document.activeElement.dataset.newsId')=='a3973b36c3edd608'
    for ident in ['a3db36de7de4297f','740fbfe776775a58','a1d9fbbdd67f650c','110baf802c1c037e','de251274a9173ea9']:
        page.goto(BASE+'?news='+ident,wait_until='networkidle')
        assert page.locator('.reader-copy section').count()==3
        assert len(page.locator('.reader-article').inner_text())>2000
        if ident in ['740fbfe776775a58','a1d9fbbdd67f650c','110baf802c1c037e']:
            assert page.locator('.reader-visual').count()==0
    page.goto(BASE+'packaging.html',wait_until='networkidle')
    total=page.evaluate('TONKO_PACKAGING.length');counts=page.evaluate('TONKO_PACKAGING.reduce((m,r)=>(m[r.brand]=(m[r.brand]||0)+1,m),{})')
    assert page.locator('#pack-brand option').count()==len(counts)+1
    assert page.locator('.pack-card').count()==sum(min(n,4) for n in counts.values())
    assert page.locator('nav a[aria-current="page"]').inner_text()=='Упаковки'
    page.screenshot(path=str(OUT/'media9-packaging-desktop.png'),full_page=True)
    page.locator('[data-more-brand="Conte"]').click();assert page.locator('[data-brand-section="Conte"] .pack-card').count()==16
    page.locator('#pack-brand').select_option('OMSA')
    assert page.locator('.pack-card').count()>20
    page.locator('#pack-search').fill('Attiva');assert page.locator('.pack-card').count()>0
    page.locator('.pack-open').first.click();assert page.locator('#pack-dialog[open]').count()==1
    page.wait_for_function('document.querySelector("#pack-full")?.naturalWidth>0')
    fit_width=page.locator('#pack-full').bounding_box()['width']
    page.locator('#pack-zoom').click();assert page.locator('#pack-zoom').get_attribute('aria-pressed')=='true'
    assert page.locator('#pack-full').bounding_box()['width']>=fit_width*1.9
    page.screenshot(path=str(OUT/'media9-pack-detail.png'))
    page.keyboard.press('Escape');assert page.evaluate('document.activeElement.matches(".pack-open")')
    page.locator('#pack-reset').click();page.locator('#pack-den').select_option('thin')
    assert page.locator('.pack-card').count()>0
    ids=page.locator('[data-pack]').evaluate_all('(a)=>a.map(x=>x.dataset.pack)')
    assert page.evaluate('(ids)=>TONKO_PACKAGING.filter(x=>ids.includes(x.id)).every(x=>x.den>0&&x.den<=20)',ids)
    page.locator('#pack-search').fill('НесуществующаяМодель');assert page.locator('.pack-card').count()==0
    assert page.locator('[data-more-brand]').count()==0
    page.goto(BASE+'packaging.html?pack=pkg-falke',wait_until='networkidle')
    assert page.locator('#pack-label').inner_text()=='FALKE'
    assert page.locator('#pack-next').is_disabled()
    page.keyboard.press('Escape')
    for width in [320,390,768,1440]:
        page.set_viewport_size({'width':width,'height':850})
        for path in ['packaging.html','?news=a3973b36c3edd608','?news=740fbfe776775a58','videos.html']:
            page.goto(BASE+path,wait_until='networkidle')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(width,path,'overflow')
            if page.locator('.news-reader[open]').count():
                assert page.locator('.news-reader').evaluate('(d)=>d.scrollWidth<=d.clientWidth+1')
            if width==390 and path=='?news=a3973b36c3edd608':page.screenshot(path=str(OUT/'media9-news-mobile.png'))
            if width==390 and path=='packaging.html':page.screenshot(path=str(OUT/'media9-packaging-mobile.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000})
    # A mock isolates our controls from Google's network/authentication decisions.
    page.add_init_script("""window.YT={Player:class {constructor(id,options){this.o=options;setTimeout(()=>options.events.onReady({target:this}),20)}getCurrentTime(){return 0}getDuration(){return 0}getPlayerState(){return 0}playVideo(){}pauseVideo(){}seekTo(){}destroy(){}}};""")
    page.route('**/embed/**',lambda route:route.fulfill(status=200,content_type='text/html',body='<p>Mock external player</p>'))
    page.goto(BASE+'videos.html?provider=youtube',wait_until='networkidle')
    page.locator('[data-video-card]:visible .video-watch-button').first.click()
    assert page.locator('.youtube-account-help').is_visible()
    assert 'youtube-nocookie.com' in page.locator('#video-screen iframe').get_attribute('src')
    page.locator('#youtube-use-account').click()
    assert 'www.youtube.com/embed/' in page.locator('#video-screen iframe').get_attribute('src')
    page.locator('#youtube-reconnect').click()
    assert 'www.youtube.com/embed/' in page.locator('#video-screen iframe').get_attribute('src')
    page.reload(wait_until='networkidle');assert page.locator('#video-youtube-mode').input_value()=='standard'
    page.goto(BASE+'videos.html?provider=native',wait_until='networkidle')
    page.locator('[data-video-card]:visible .video-watch-button').first.click()
    assert not page.locator('.youtube-account-help').is_visible()
    assert page.locator('#video-screen video').count()==1
    assert not errors,errors
    context.close()
    nojs=browser.new_context(java_script_enabled=False)
    page=nojs.new_page();page.goto(BASE+'news.html#story-a3973b36c3edd608')
    assert page.locator('#story-a3973b36c3edd608 h3').count()==3
    assert len(page.locator('#story-a3973b36c3edd608').inner_text())>2500
    page.goto(BASE+'packaging.html');assert page.locator('.pack-card').count()==total
    browser.close()
print(json.dumps({'status':'PASS','packages':total,'brands':len(counts),'expandedArticles':6,'viewports':[320,390,768,1440],'javascriptErrors':errors,'youtube':'UI/host/mode persistence tested with mock; no claim of Google login'},ensure_ascii=False))
