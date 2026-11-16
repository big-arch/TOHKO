"""Real Chromium layout and deep-link checks for the new sourced photo collection."""
import json,sys,functools,threading
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SITE=ROOT/'tights-guide'
sys.path.insert(0,str(ROOT/'.cache/pw-runtime'))
from playwright.sync_api import sync_playwright

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def main():
    output=ROOT/'.cache/style14';output.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(SITE)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}';errors=[];checks=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel='chrome',headless=True)
            context=browser.new_context(viewport={'width':1440,'height':1000})
            context.route('**/*',lambda route:route.continue_() if route.request.url.startswith(origin) else route.abort())
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            for width in [1440,390,320]:
                page.set_viewport_size({'width':width,'height':950})
                page.goto(origin+'/men.html#men-photo-collection')
                page.locator('#men-photo-collection').wait_for()
                assert page.locator('#men-photo-collection figure').count()==9
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                for img in page.locator('#men-photo-collection img').all():
                    img.scroll_into_view_if_needed();page.wait_for_function('(i)=>i.complete&&i.naturalWidth>0',arg=img.element_handle())
                page.locator('#men-photo-collection').screenshot(path=str(output/f'men-{width}.png'))
                page.goto(origin+'/lookbook.html?filter=men-sheer')
                page.wait_for_function('document.querySelectorAll(".gallery-item").length===5')
                titles=page.locator('.gallery-item h2').all_text_contents()
                assert all('Glamory' in x or 'NYLO' in x for x in titles)
                page.locator('.gallery-open').first.click()
                page.wait_for_function('document.querySelector("#editorial-full-image").naturalWidth>0')
                assert page.locator('#editorial-lightbox').evaluate('(x)=>x.open')
                page.keyboard.press('Escape')
                page.goto(origin+'/lookbook.html?filter=couple')
                page.wait_for_function('document.querySelectorAll(".gallery-item").length===2')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                checks.append({'width':width,'photos':9,'verifiedDensity':5,'couple':2,'horizontalOverflow':False})
            page.goto(origin+'/lookbook.html#photo-style-couple-city')
            page.wait_for_function('document.querySelector("#editorial-lightbox").open')
            assert page.locator('#editorial-photo-title').inner_text()=='Вдвоём на городской прогулке'
            assert 'Плотность' in page.locator('#editorial-photo-caption').inner_text()
            assert not errors,errors
            browser.close()
        report={'passed':True,'checks':checks,'deepLink':True,'jsErrors':errors}
        (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False))
    finally:server.shutdown()

if __name__=='__main__':main()
