"""Regression cases for the headline-only backlog and bounded retries."""
import copy
import sys
import unittest
from datetime import timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from news_ai import enrich
from news_render import story
from test_news_ai import NOW, SOURCE, TEXT, item, result
from test_news import rss
from news_feed import collect
from news_sources import resolve_publisher,publisher_source,SourceError,GooglePublisherRedirect
from news_ai import MAX_PAID_ATTEMPTS,article_cover,APIError,MAX_PER_DAY

class QueueTests(unittest.TestCase):
    def test_resolved_google_story_is_prepared_from_publisher_text(self):
        google={'id':'google','site':'https://news.google.com','publishers':['example.org']}
        entry={**item(),'sourceId':'google','url':'https://news.google.com/rss/articles/123',
               'via':'Google News','sourceSite':'https://example.org','publisherUrl':'https://example.org/one'}
        calls=[];news={'items':[entry]}
        enrich(news,[google],{},lambda i:TEXT,lambda i,t:(calls.append(i['id']) or result()),NOW)
        self.assertEqual(calls,['one'])
        self.assertEqual(entry['publication']['status'],'ready')

    def test_failed_sources_are_counted_and_retried_without_paid_calls(self):
        news={'items':[item()]};cache={};fetches=[]
        def offline(i):fetches.append(i['id']);raise OSError('offline')
        for stamp in (NOW,NOW+timedelta(minutes=15),NOW+timedelta(hours=1)):
            enrich(news,[SOURCE],cache,offline,lambda *a:self.fail('No paid request'),stamp)
        self.assertEqual(len(fetches),2)
        state=news['items'][0]['publication']
        self.assertEqual(state['status'],'failed')
        self.assertEqual(state['fetchAttempts'],2)
        self.assertIn('nextAttemptAt',state)
        self.assertEqual(cache['calls'],0)

    def test_snapshot_retains_retry_state_without_private_cache(self):
        news={'items':[item()]}
        def offline(i):raise OSError('offline')
        enrich(news,[SOURCE],{},offline,lambda *a:self.fail('No API'),NOW)
        enrich(news,[SOURCE],{},lambda *a:self.fail('Wait for backoff'),lambda *a:self.fail('No API'),NOW+timedelta(minutes=15))
        self.assertEqual(news['items'][0]['publication']['fetchAttempts'],1)

    def test_unprepared_story_is_not_a_readable_article(self):
        self.assertEqual(story(item()),'')

    def test_refresh_keeps_queue_metadata(self):
        source={**SOURCE,'name':'Example','url':'https://example.org/feed','language':'en','mode':'topic'}
        old=collect([source],{},lambda s:rss(link='https://example.org/one'),NOW)
        state={'status':'failed','reason':'source_unavailable','fetchAttempts':2,'nextAttemptAt':'2026-11-17T00:00:00Z'}
        old['items'][0]['publication']=state
        fresh=collect([source],old,lambda s:rss(link='https://example.org/one'),NOW)
        self.assertEqual(fresh['items'][0].get('publication'),state)

    def test_ready_story_wins_over_new_duplicate_without_a_body(self):
        from news_feed import merge_items
        ready={**item(),**result(),'via':'Google News','url':'https://news.google.com/rss/articles/123','publisherUrl':'https://example.org/one'}
        direct={**item('new'),'url':'https://example.org/one'}
        self.assertEqual(merge_items([direct,ready],NOW)[0]['id'],'one')

    def test_google_resolves_exact_title_from_publisher_feed(self):
        source={**SOURCE,'name':'Example','url':'https://example.org/feed','language':'en','mode':'topic'}
        google={'id':'google','site':'https://news.google.com','publishers':['example.org']}
        entry={**item(),'title':'New patterned tights','sourceId':'google','url':'https://news.google.com/rss/articles/123','via':'Google News','sourceSite':'https://example.org'}
        url,publisher=resolve_publisher(entry,[source,google],lambda u,s:rss(),NOW,follow_google=lambda *a:self.fail('Feed resolved it'))
        self.assertEqual(url,'https://example.org/story')
        self.assertEqual(entry['publisherUrl'],url)
        self.assertEqual(publisher['id'],'example')

    def test_google_never_resolves_to_unapproved_publisher(self):
        source={**SOURCE,'name':'Example','language':'en','mode':'topic'}
        google={'id':'google','site':'https://news.google.com','publishers':['example.org']}
        entry={**item(),'sourceId':'google','url':'https://news.google.com/rss/articles/123','via':'Google News','sourceSite':'https://evil.org'}
        with self.assertRaises(SourceError):publisher_source(entry,[source,google])
        entry['sourceSite']='https://example.org'
        with self.assertRaises(SourceError):resolve_publisher(entry,[source,google],lambda *a:self.fail('No feed'),NOW,follow_google=lambda *a:'https://evil.org/story')
        from urllib.request import Request
        with self.assertRaises(SourceError):GooglePublisherRedirect(source).redirect_request(Request(entry['url']),None,302,'Found',{},'https://evil.org')

    def test_rejected_copy_is_not_repeatedly_paid_for(self):
        news={'items':[item()]};cache={};calls=[]
        def reject(i,t):calls.append(i['id']);return {'usable':False}
        for day in (0,1,2,3,10):enrich(news,[SOURCE],cache,lambda i:TEXT,reject,NOW+timedelta(days=day))
        self.assertEqual(len(calls),MAX_PAID_ATTEMPTS)
        self.assertEqual(news['items'][0]['publication']['status'],'failed')
        self.assertNotIn('sections',news['items'][0])

    def test_changed_source_can_recover_after_rejection(self):
        news={'items':[item()]};cache={}
        for day in range(3):enrich(news,[SOURCE],cache,lambda i:TEXT,lambda *a:{'usable':False},NOW+timedelta(days=day))
        enrich(news,[SOURCE],cache,lambda i:TEXT+' Новая подтверждённая деталь.',lambda *a:result(),NOW+timedelta(days=10))
        self.assertEqual(news['items'][0]['publication']['status'],'ready')

    def test_short_but_complete_source_can_make_a_short_article(self):
        text=' '.join('source'+str(n) for n in range(150))
        answer={'usable':True,'displayTitle':'Небольшая коллекция новых колготок','summary':'Марка представила новую коллекцию и объяснила подход к её оформлению.',
                'sections':[{'heading':'Подробности выпуска','paragraphs':[' '.join(['В публикации описаны цвета модели и участники подготовки коллекции.']*8)]}]}
        news={'items':[item()]}
        enrich(news,[SOURCE],{},lambda i:text,lambda i,t:answer,NOW)
        self.assertEqual(news['items'][0]['publication']['status'],'ready')

    def test_winter_og_needs_editorial_review(self):
        self.assertIsNone(article_cover('<meta property="og:image" content="https://example.org/summer.jpg">',SOURCE,{**item(),'title':'Winter leggings trends'}))

    def test_winter_feed_cover_also_needs_review(self):
        from news_feed import parse_feed
        source={**SOURCE,'name':'Example','url':'https://example.org/feed','language':'en','mode':'topic'}
        raw=rss(title='Winter tights ideas').replace(b'<rss>',b'<rss xmlns:media="http://search.yahoo.com/mrss/">').replace(b'</item>',b'<media:content medium="image" url="https://example.org/summer.jpg" width="800" height="1000"/></item>')
        self.assertNotIn('illustration',parse_feed(raw,source,NOW)[0])

    def test_public_daily_ledger_cannot_be_reset_by_losing_cache(self):
        news={'items':[item()],'aiUsage':{'date':NOW.date().isoformat(),'calls':MAX_PER_DAY}}
        enrich(news,[SOURCE],{},lambda *a:self.fail('Daily limit'),lambda *a:self.fail('No paid requests'),NOW)
        self.assertEqual(news['items'][0]['publication']['status'],'pending')

    def test_archive_retains_ready_articles_after_one_year_and_over_sixty_items(self):
        from news_feed import merge_items
        archive=[{**item(str(n)),'title':'News '+str(n),**result(),'publishedAt':'2025-01-01T10:00:00Z'} for n in range(75)]
        self.assertEqual(len(merge_items(archive,NOW)),75)
        self.assertEqual(merge_items([{**item(),'publishedAt':'2025-01-01T10:00:00Z'}],NOW),[])

    def test_pending_backlog_cannot_evict_a_published_deep_link(self):
        from news_feed import merge_items
        archived={**item('archived'),'title':'An older completed tights article',**result(),'publishedAt':'2025-01-01T10:00:00Z'}
        pending=[{**item(str(n)),'title':'Pending news '+str(n)} for n in range(220)]
        merged=merge_items(pending+[archived],NOW)
        self.assertIn('archived',{i['id'] for i in merged})
        self.assertEqual(sum(not bool(i.get('sections')) for i in merged),200)
        complete=[{**item(str(n)),'title':'Ready news '+str(n),**result()} for n in range(205)]
        self.assertEqual(len(merge_items(complete+[archived],NOW)),200)

    def test_api_recovery_survives_an_intermediate_source_failure(self):
        news={'items':[item()]};cache={};calls=[]
        def unavailable(i,t):raise APIError(401)
        for minutes in (0,30,60):enrich(news,[SOURCE],cache,lambda i:TEXT,unavailable,NOW+timedelta(minutes=minutes))
        def offline(i):raise OSError('Publisher unavailable')
        enrich(news,[SOURCE],cache,offline,lambda *a:self.fail('No source'),NOW+timedelta(days=8))
        enrich(news,[SOURCE],cache,lambda i:TEXT,lambda i,t:(calls.append(i['id']) or result()),NOW+timedelta(days=16))
        self.assertEqual(calls,['one'])
        self.assertEqual(news['items'][0]['publication']['status'],'ready')

    def test_photo_backfill_runs_even_when_ai_is_disabled(self):
        import importlib.util,json,tempfile
        from unittest.mock import patch
        path=Path(__file__).resolve().parents[1]/'scripts/enrich-news.py'
        spec=importlib.util.spec_from_file_location('enrich_news_cli',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)
            (data/'news.json').write_text(json.dumps({'items':[item()]}),encoding='utf-8')
            (data/'news-sources.json').write_text(json.dumps([SOURCE]),encoding='utf-8')
            with patch.object(module,'DATA',data),patch.object(module,'backfill_covers',return_value={'checked':1,'added':0}) as fill,patch.dict('os.environ',{'OPENAI_NEWS_ENABLED':'false'}):
                module.main();fill.assert_called_once()

if __name__=='__main__':unittest.main()
