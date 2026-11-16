"""Three real AI turns, official production Origin; local static assets only may be routed."""
import argparse,json,mimetypes,sys
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1];SITE=ROOT/'tights-guide'
sys.path.insert(0,str(ROOT/'.cache/pw-runtime'))
from playwright.sync_api import sync_playwright,expect
BASE='https://big-arch.github.io/TOHKO/'

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--public',action='store_true');args=parser.parse_args()
    output=ROOT/'.cache/assistant14-live';output.mkdir(exist_ok=True)
    config=json.loads((SITE/'data/assistant-config.json').read_text(encoding='utf-8'));endpoint=config['endpoint']
    report={'checkedAt':datetime.now(timezone.utc).isoformat(),'static':'public' if args.public else 'local assets at production Origin','apiMocked':False,'turns':[],'jsErrors':[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1080})
        def route_local(route):
            path=(SITE/unquote(urlsplit(route.request.url).path.removeprefix('/TOHKO/'))).resolve()
            if path==SITE.resolve():path=path/'index.html'
            if SITE.resolve() not in path.parents or not path.is_file():return route.fulfill(status=404,body='Not found')
            route.fulfill(status=200,body=path.read_bytes(),content_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        if not args.public:context.route(BASE+'**',route_local)
        for host in ['fonts.googleapis.com','fonts.gstatic.com','unpkg.com']:context.route('https://'+host+'/**',lambda route:route.abort())
        page=context.new_page();page.on('pageerror',lambda e:report['jsErrors'].append(str(e)))
        page.goto(BASE+'index.html',wait_until='domcontentloaded')
        page.get_by_role('button',name='Спросить ТОНКО').click()
        questions=['Покажи два фото мужчин в прозрачных колготках 20 DEN.','А на втором снимке какая плотность и как сочетать такие колготки с шортами?','Теперь покажи фото мужчины и девушки вместе.']
        for index,question in enumerate(questions):
            field=page.locator('#tonko-assistant-input');field.fill(question)
            send=page.get_by_role('button',name='Отправить вопрос');expect(send).to_be_enabled(timeout=15000)
            with page.expect_response(lambda r:r.url==endpoint and r.request.method=='POST',timeout=60000) as waited:send.click()
            response=waited.value;data=response.json()
            report['turns'].append({'question':question,'status':response.status,'response':data})
            (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            assert response.status==200,{'status':response.status,'error':data.get('error')}
            expect(page.locator('.tonko-assistant-message.is-assistant')).to_have_count(index+1)
            if index==0:
                assert len(data.get('photos',[]))==2
                assert all(p['category']=='men' and p['den']==20 and p['denVerified'] for p in data['photos'])
                for img in page.locator('.tonko-assistant-photo img').all():
                    img.scroll_into_view_if_needed();page.wait_for_function('(x)=>x.complete&&x.naturalWidth>0',arg=img.element_handle())
                page.locator('.tonko-assistant-photo-open').first.click();page.screenshot(path=str(output/'zoom-desktop.png'));page.keyboard.press('Escape')
            if index==1:assert '20' in data['answer']
            if index==2:assert data.get('photos') and all(p['category']=='couple' for p in data['photos'])
        page.screenshot(path=str(output/'conversation-desktop.png'))
        page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(output/'conversation-mobile.png'))
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert not report['jsErrors']
        report['passed']=True;(output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False));browser.close()

if __name__=='__main__':main()
