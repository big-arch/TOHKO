"""Offline Chrome QA for publication dates, chronological feeds and expiry.

All external requests are blocked. Synthetic articles exist only in browser routes.
No news collection, provider or AI service is called; production data is untouched.
"""
import functools
import json
import re
import sys
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT/'tights-guide'
for runtime in (ROOT/'.cache/pw-runtime', Path('C:/Users/Артур/Documents/CODEX_сайт_ТОНКО/.cache/pw-runtime')):
    if runtime.is_dir():
        sys.path.insert(0, str(runtime)); break
from playwright.sync_api import expect, sync_playwright

NOW = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
NOW_MS = int(NOW.timestamp()*1000)
DAY = 24*60*60*1000
SNAPSHOT = json.loads((SITE/'data/news.json').read_text('utf-8'))
JOURNAL = json.loads((SITE/'data/journal.js').read_text('utf-8').split('=', 1)[1].strip().rstrip(';'))


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass  # A page navigation may cancel lazy images still being served.


def fixture_item(ident, stamp, language='ru'):
    return {'id':ident, 'title':'Публикация '+ident, 'source':'Тестовый источник', 'url':'https://example.org/'+ident,
            'publishedAt':stamp, 'language':language, 'checkedAt':'2026-11-17T12:00:00Z',
            'summary':'Подробный разбор фактуры, конструкции и сочетаний колготок в гардеробе.',
            'sections':[{'heading':'О публикации', 'paragraphs':['Осознанный выбор начинается с изучения состава ткани и конструкции изделия. '*12]}]}


def visible_ids(page, selector, attribute):
    return page.locator(selector+':visible').evaluate_all('(rows, key)=>rows.map(row=>row.getAttribute(key))', attribute)


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(SITE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    errors, checks, blocked = [], [], []

    def route_external(route):
        if route.request.url.startswith(origin+'/'):
            route.continue_()
        else:
            blocked.append(route.request.url); route.abort()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context(viewport={'width':1440,'height':1000}, reduced_motion='reduce', timezone_id='Europe/Moscow')
        context.route('**/*', route_external)
        context.add_init_script(f'window.__publicationNow={NOW_MS}; Date.now=()=>window.__publicationNow;')
        page = context.new_page(); page.on('pageerror', lambda e: errors.append(str(e)))

        # Real assets, real saved feed, all requested layouts, with dates visible on mobile.
        for width in (320,390,768,1440):
            page.set_viewport_size({'width':width,'height':1000})
            for name, selector in (('index.html','#news-list .publication-meta'), ('news.html','.news-fallback .publication-meta'),
                                   ('journal.html','#journal-list .publication-meta'), ('read-light.html','.story-byline .publication-meta')):
                page.goto(origin+'/'+name, wait_until='domcontentloaded')
                if name == 'news.html':
                    page.evaluate('scrollTo(0,0)')
                    header = page.locator('.portal-header').bounding_box()
                    eyebrow = page.locator('.news-archive>.portal-eyebrow').bounding_box()
                    heading = page.locator('main h1').bounding_box()
                    assert eyebrow['y'] >= header['y']+header['height']+31, (width,'news header needs top spacing')
                    assert heading['y'] >= eyebrow['y']+eyebrow['height'], (width,'news heading overlaps eyebrow')
                    if width == 390:
                        page.screenshot(path=str(ROOT/'qa/news17-news-top-390.png'))
                meta = page.locator(selector).first
                expect(meta).to_be_visible(); meta.scroll_into_view_if_needed()
                assert meta.locator('time').get_attribute('datetime'), (name,width,'no time')
                assert meta.bounding_box()['width'] <= width, (name,width,'metadata overflow')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), (name,width,'document overflow')
                assert page.locator('.publication-meta time').first.get_attribute('aria-label').startswith('Дата публикации:')
                if width == 390:
                    page.screenshot(path=str(ROOT/'qa'/('news17-'+name.replace('.html','')+'-390.png')))
            checks.append(f'real pages at {width}px')

        # Changing the arrival/check order must not change chronology.
        items = [fixture_item('unknown',None), fixture_item('old','2025-01-01T00:00:00Z'),
                 fixture_item('tie-a','2026-11-16T12:00:00Z','en'), fixture_item('expired','2026-11-10T12:00:00Z'),
                 fixture_item('invalid','2026-02-30'), fixture_item('future','2026-11-18T00:00:00Z','en'),
                 fixture_item('tie-b','2026-11-16T15:00:00+03:00'), fixture_item('recent','2026-11-17T11:00:00Z'),
                 fixture_item('almost-expired','2026-11-10T12:00:00.001Z')]
        data = {'version':1,'items':items,'sources':[], 'lastSuccessfulAt':'2026-11-17T12:00:00Z'}
        html = (SITE/'index.html').read_text('utf-8')
        def fixture_home(route):
            body = re.sub(r'(<script id="news-seed"[^>]*>).*?(</script>)', lambda m:m[1]+json.dumps(data,ensure_ascii=False)+m[2], html, flags=re.S)
            route.fulfill(status=200, content_type='text/html; charset=utf-8', body=body)
        page.route('**/index.html*', fixture_home)
        page.route('**/data/news.json*', lambda route:route.fulfill(status=200,json=data))
        page.goto(origin+'/index.html', wait_until='domcontentloaded')
        expect(page.locator('#news-list .news-item')).to_have_count(6)
        first = ['future','recent','tie-a','tie-b','almost-expired','expired']
        ids = lambda:page.locator('#news-list [data-news-id]').evaluate_all('(links)=>links.map(link=>link.dataset.newsId)')
        assert ids() == first, ids()
        expect(page.locator('#news-list [data-publication-new]:visible')).to_have_count(4)
        expect(page.locator('[data-news-id="future"]').locator('xpath=ancestor::article').locator('[data-publication-new]')).to_be_hidden()
        page.locator('#news-more').click()
        assert ids() == first+['old','unknown','invalid'], ids()
        expect(page.locator('#news-list .publication-undated')).to_have_count(2)
        page.locator('[data-news-language="en"]').click()
        assert ids() == ['future','tie-a']
        page.locator('[data-news-language="ru"]').click()
        assert ids() == ['recent','tie-b','almost-expired','expired','old','unknown']
        page.locator('[data-news-language="all"]').click()
        assert ids() == first
        checks.append('unsorted feed, ties, unknown/invalid last, language filters, pagination')

        # Reader metadata agrees with card metadata; it also expires while the dialog remains open.
        page.set_viewport_size({'width':320,'height':1000})
        page.locator('[data-news-id="recent"]').click()
        dialog = page.locator('.news-reader[open]'); expect(dialog).to_be_visible()
        assert dialog.locator('time').get_attribute('datetime') == '2026-11-17T11:00:00Z'
        expect(dialog.locator('[data-publication-new]')).to_be_visible()
        assert dialog.evaluate('(node)=>node.scrollWidth<=node.clientWidth+1')
        page.screenshot(path=str(ROOT/'qa/news17-modal-320.png'))
        page.evaluate('(now)=>{window.__publicationNow=now;document.dispatchEvent(new Event("visibilitychange"));}', NOW_MS+8*DAY)
        expect(dialog.locator('[data-publication-new]')).to_be_hidden()
        assert page.locator('[data-news-language="all"]').get_attribute('aria-pressed') == 'true'
        page.keyboard.press('Escape'); expect(dialog).to_have_count(0)
        page.evaluate('(now)=>{window.__publicationNow=now;dispatchEvent(new Event("pageshow"));}', NOW_MS)
        expect(page.locator('#news-list [data-publication-new]:visible')).to_have_count(4)
        checks.append('mobile modal time, future exclusion, expiry on visibility/pageshow without reset')

        # A refreshed snapshot is deliberately reversed; apply updates and preserve chronology.
        data['items'] = [*reversed(items),fixture_item('arriving','2026-11-17T11:59:00Z')]
        page.locator('#news-refresh').click()
        expect(page.locator('#news-new')).to_be_visible()
        assert ids() == first
        page.locator('#news-new').click()
        assert ids() == ['future','arriving','recent','tie-b','tie-a','almost-expired']
        checks.append('manual refresh queues changes and sorts by original publication time')

        # Journal uses metadata dates, not its visual issue order or saved-reading timestamps.
        journal = [dict(i) for i in JOURNAL]
        values = {'light':'2020-01-01','patterns':'2026-11-16','construction':None,
                  'product-card':'2026-11-18','making':'2026-02-30','archive':'2026-11-11'}
        for item in journal:item['publishedAt']=values[item['id']]
        page.route('**/data/journal.js*', lambda route:route.fulfill(content_type='text/javascript', body='window.TONKO_JOURNAL = '+json.dumps(journal,ensure_ascii=False)+';'))
        page.goto(origin+'/journal.html', wait_until='domcontentloaded')
        expected = ['product-card','patterns','archive','light','construction','making']
        assert visible_ids(page,'#journal-list [data-story]','data-story') == expected
        expect(page.locator('#journal-list .publication-undated')).to_have_count(2)
        page.locator('[data-journal-filter="Стиль"]').click()
        assert visible_ids(page,'#journal-list [data-story]','data-story') == ['patterns']
        page.locator('[data-save-story="patterns"]').click()
        page.locator('[data-journal-filter="saved"]').click()
        assert visible_ids(page,'#journal-list [data-story]','data-story') == ['patterns']
        page.locator('[data-journal-filter="all"]').click()
        assert visible_ids(page,'#journal-list [data-story]','data-story') == expected
        checks.append('journal chronology, unknown fallback, themes and saved filter')

        # A browser with the previous metadata cache still has authoritative SSR dates.
        cached_journal = [{k:v for k,v in item.items() if k!='publishedAt'} for item in JOURNAL]
        page.unroute('**/data/journal.js*')
        page.route('**/data/journal.js*', lambda route:route.fulfill(content_type='text/javascript', body='window.TONKO_JOURNAL = '+json.dumps(cached_journal,ensure_ascii=False)+';'))
        page.goto(origin+'/journal.html', wait_until='domcontentloaded')
        assert page.locator('#journal-list time').evaluate_all('(rows)=>rows.map(row=>row.dateTime)') == ['2026-11-15']*6
        checks.append('older journal metadata cache preserves confirmed SSR dates')

        # Direct boundary validation complements the visible feed cases.
        result = page.evaluate('''(now)=>{
          const dates=window.TonkoPublication;
          return {invalid:['',null,'bad','2026-02-30','0000-01-01','2026-11-17T24:00:00Z','2026-11-17T12:00:00'].map(v=>dates.timestamp(v)),
            boundaries:[now+1,now,now-7*86400000+1,now-7*86400000].map(n=>dates.isNew(new Date(n).toISOString(),now))};
        }''', NOW_MS)
        assert result['invalid'] == [None]*7, result
        assert result['boundaries'] == [False,True,True,False], result
        checks.append('client date validation and exact seven-day boundary')

        # The periodic refresh retires a badge with no interaction or navigation.
        timer_context = browser.new_context(timezone_id='Pacific/Honolulu')
        timer_context.route('**/*', route_external)
        timer = timer_context.new_page()
        timer.clock.install(time=NOW)
        timer.set_content('<main id="dates"></main>')
        timer.add_script_tag(path=str(SITE/'publication-dates.js'))
        timer.evaluate('document.querySelector("#dates").append(TonkoPublication.create("2026-11-10T12:00:30Z"),TonkoPublication.create("2026-11-15"))')
        expect(timer.locator('[data-publication-new]').first).to_be_visible()
        assert timer.locator('time').last.text_content().startswith('15 ноября'), 'date-only must not shift in another timezone'
        timer.clock.fast_forward(60001)
        expect(timer.locator('[data-publication-new]').first).to_be_hidden()
        timer_context.close()
        checks.append('periodic expiry without interaction; date-only label independent of local timezone')

        # Disabled-JS pages retain accessible dates and the same saved chronology.
        nojs = browser.new_context(java_script_enabled=False, viewport={'width':390,'height':1000})
        nojs.route('**/*', route_external)
        static = nojs.new_page()
        ready = [i for i in SNAPSHOT['items'] if i.get('sections')]
        ready.sort(key=lambda i:datetime.fromisoformat(i['publishedAt'].replace('Z','+00:00')), reverse=True)
        for name, selector in (('index.html','#news-list time'),('news.html','.news-fallback time'),('journal.html','#journal-list time')):
            static.goto(origin+'/'+name, wait_until='domcontentloaded')
            expected_dates = [i['publishedAt'] for i in ready[:6]] if name=='index.html' else [i['publishedAt'] for i in ready] if name=='news.html' else ['2026-11-15']*6
            assert static.locator(selector).evaluate_all('(rows)=>rows.map(row=>row.dateTime)') == expected_dates, name
            assert static.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), name
        for item in JOURNAL:
            static.goto(origin+'/'+item['url'],wait_until='domcontentloaded')
            assert static.locator('.story-byline time').get_attribute('datetime')=='2026-11-15'
        checks.append('no-JS home/full-news/journal order and all six reader dates')
        nojs.close(); context.close(); browser.close()
    server.shutdown()
    assert not errors, errors
    report = {'status':'PASS','checks':checks,'javascriptErrors':errors,'externalRequestsBlocked':len(blocked),
              'networkPolicy':'All external requests blocked; no provider/AI calls.'}
    (ROOT/'qa/news17-browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()
