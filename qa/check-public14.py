"""Check release14 on real GitHub Pages; one genuine assistant question."""
import json,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.cache/pw-runtime'));sys.path.insert(0,str(ROOT/'scripts'))
from playwright.sync_api import sync_playwright
from news_publication import is_ready
BASE='https://big-arch.github.io/TOHKO/'

def main():
    out=ROOT/'.cache/public14';out.mkdir(exist_ok=True)
    report={'checkedAt':datetime.now(timezone.utc).isoformat(),'site':BASE,'apiMocked':False,'jsErrors':[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000})
        page=context.new_page();page.on('pageerror',lambda e:report['jsErrors'].append(str(e)))
        page.goto(BASE+'index.html?release=14',wait_until='domcontentloaded')
        def data(name):
            r=page.request.get(BASE+'data/'+name+'?release=14');assert r.status==200,(name,r.status);return r.json()
        styles=data('style-photos.json');looks=data('package-looks.json');videos=data('videos.json');news=data('news.json');knowledge=data('assistant-knowledge.json')
        assert len(styles['items'])==13 and len(looks['items'])==30
        assert len(knowledge['photos'])==117 and len(videos)>=26
        ready=[i for i in news['items'] if is_ready(i)]
        report.update(stylePhotos=13,packageModels=30,packagePhotos=sum(len(x['photos']) for x in looks['items']),videos=len(videos),readyNews=len(ready),pendingNews=len(news['items'])-len(ready),assistantPhotos=len(knowledge['photos']),newsCheckedAt=news['checkedAt'],videoState=data('video-feed-state.json'))
        page.goto(BASE+'lookbook.html?filter=men-sheer')
        page.wait_for_function('document.querySelectorAll(".gallery-item").length===5')
        page.locator('.gallery-open').first.click();page.wait_for_function('document.querySelector("#editorial-full-image").naturalWidth>0')
        page.screenshot(path=str(out/'gallery.png'));page.keyboard.press('Escape')
        page.goto(BASE+'packaging.html?pack=pkg-03eff8abf3')
        page.wait_for_function('document.querySelector("#pack-dialog").open')
        images=page.locator('#pack-dialog img[src^="assets/package-looks/"]');assert images.count()==4
        for img in images.all():
            img.scroll_into_view_if_needed();page.wait_for_function('(x)=>x.complete&&x.naturalWidth>0',arg=img.element_handle())
        page.screenshot(path=str(out/'wolford.png'))
        page.goto(BASE+'videos.html')
        assert page.get_by_text('Использовать обычный YouTube',exact=True).count()==0
        assert page.get_by_text('Обновить плеер после входа',exact=True).count()==0
        page.locator('[data-video-play="snag-motion"]:visible').first.click()
        page.wait_for_function('document.querySelector("#video-screen video")?.currentTime>1',timeout=30000)
        report['nativePlayback']=page.locator('#video-screen video').evaluate('(v)=>({time:v.currentTime,paused:v.paused,readyState:v.readyState,error:v.error?.code||null})')
        page.goto(BASE+'news.html#story-ee8ae4a2a6c7f547')
        winter=page.locator('#story-ee8ae4a2a6c7f547');winter.scroll_into_view_if_needed()
        img=winter.locator('.reader-visual img');img.scroll_into_view_if_needed();page.wait_for_function('(x)=>x.naturalWidth>0',arg=img.element_handle())
        assert 'winter-leggings-coat-boots' in img.get_attribute('src')
        assert img.bounding_box()['width']>700
        page.goto(BASE+'index.html');page.get_by_role('button',name='Спросить ТОНКО').click()
        page.locator('#tonko-assistant-input').fill('Покажи фото модели Wolford Individual 20, а не только упаковку.')
        config=data('assistant-config.json')
        with page.expect_response(lambda r:r.url==config['endpoint'] and r.request.method=='POST',timeout=60000) as waiting:page.get_by_role('button',name='Отправить вопрос').click()
        r=waiting.value;answer=r.json();report['assistant']={'status':r.status,**answer};assert r.status==200
        assert answer.get('photos') and all(p.get('model')=='Individual 20' for p in answer['photos'])
        for img in page.locator('.tonko-assistant-photo img').all():
            img.scroll_into_view_if_needed();page.wait_for_function('(x)=>x.naturalWidth>0',arg=img.element_handle())
        page.screenshot(path=str(out/'assistant.png'));page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'assistant-mobile.png'))
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert not report['jsErrors'],report['jsErrors']
        browser.close()
    report['passed']=True;(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['assistant','videoState']},ensure_ascii=False))

if __name__=='__main__':main()
