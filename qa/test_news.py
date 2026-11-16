import sys
import unittest
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from news_feed import parse_feed, merge_items, collect, safe_url
from news_editorial import apply_editorial
from news_render import story
spec=importlib.util.spec_from_file_location('update_news',Path(__file__).resolve().parents[1]/'scripts/update-news.py')
updater=importlib.util.module_from_spec(spec);spec.loader.exec_module(updater)

NOW = datetime(2026, 11, 16, tzinfo=timezone.utc)
SOURCE = {'id':'test','name':'Test','url':'https://example.org/feed','site':'https://example.org','language':'en','mode':'topic'}
def rss(title='New patterned tights', link='https://example.org/story?utm_source=rss', date='Sun, 15 Nov 2026 12:00:00 GMT'):
    return f'<rss><channel><item><title>{title}</title><link>{link}</link><pubDate>{date}</pubDate></item></channel></rss>'.encode()

class NewsTests(unittest.TestCase):
    def test_editorial_survives_successful_feed_refresh(self):
        url='https://bracatus.com/kak-ranshe-borolis-s-neprochnostyu-chulok-kak-eto-delayut-sejchas'
        source={**SOURCE,'id':'bracatus','site':'https://bracatus.com'}
        old=collect([source],{},lambda s:rss(link=url),NOW)
        apply_editorial(old)
        updated=collect([source],old,lambda s:rss(link=url),NOW)
        apply_editorial(updated)
        item=updated['items'][0]
        self.assertEqual(len(item['sections']),3)
        self.assertEqual(item['publishedAt'],'2026-11-15T12:00:00Z')
        self.assertIn('pkg-a003df0fca',item['illustration']['src'])
        self.assertNotIn('ss-clara',story(item))
    def test_static_reader_escapes_text_and_keeps_source(self):
        item=parse_feed(rss(),SOURCE,NOW)[0]
        item.update(summary='<script>alert(1)</script>',sections=[{'heading':'Details','paragraphs':['<b>test</b>']}])
        rendered=story(item)
        self.assertNotIn('<script>',rendered)
        self.assertIn('&lt;script&gt;',rendered)
        self.assertIn('https://example.org/story',rendered)
    def test_publisher_announcement_wins_over_aggregator_duplicate(self):
        direct=parse_feed(rss(),SOURCE,NOW)[0]
        direct['excerpt']='A useful publisher announcement.'
        google={**direct,'id':'google','url':'https://news.google.com/story','via':'Google News','excerpt':''}
        self.assertEqual(merge_items([google,direct],NOW),[direct])
    def test_excerpt_is_short_plain_text(self):
        raw=rss().replace(b'</item>', ('<description>&lt;b&gt;'+('Fine tights for everyday outfits. '*30)+'&lt;/b&gt;</description></item>').encode())
        item=parse_feed(raw,SOURCE,NOW)[0]
        self.assertLessEqual(len(item['excerpt']),281)
        self.assertNotIn('<b>',item['excerpt'])
        self.assertTrue(item['excerpt'].endswith('…'))
    def test_rss_and_tracking(self):
        item = parse_feed(rss(), SOURCE, NOW)[0]
        self.assertEqual(item['url'], 'https://example.org/story')
        self.assertEqual(item['publishedAt'], '2026-11-15T12:00:00Z')
    def test_only_publisher_featured_image_is_used(self):
        raw=rss().replace(b'<rss>',b'<rss xmlns:media="http://search.yahoo.com/mrss/">').replace(b'</item>',b'<media:content medium="image" url="https://example.org/photo.jpg" width="800" height="1000"/></item>')
        self.assertEqual(parse_feed(raw,SOURCE,NOW)[0]['illustration']['src'],'https://example.org/photo.jpg')
        for url in [b'https://evil.org/photo.jpg',b'javascript:alert(1)',b'https://example.org/logo.jpg',b'https://user:pass@example.org/photo.jpg']:
            self.assertNotIn('illustration',parse_feed(raw.replace(b'https://example.org/photo.jpg',url),SOURCE,NOW)[0])
        self.assertNotIn('illustration',parse_feed(raw.replace(b'width="800"',b'width="1"'),SOURCE,NOW)[0])
    def test_missing_image_does_not_get_an_unrelated_gallery_photo(self):
        self.assertNotIn('illustration',parse_feed(rss(),SOURCE,NOW)[0])
    def test_atom_uses_publication_not_modified_date(self):
        raw=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>New tights</title><link href="https://example.org/story"/><published>2026-11-14T12:00:00+02:00</published><updated>2026-11-15T12:00:00Z</updated></entry></feed>'
        self.assertEqual(parse_feed(raw,SOURCE,NOW)[0]['publishedAt'],'2026-11-14T10:00:00Z')
    def test_unrelated_future_undated_rejected(self):
        self.assertEqual(parse_feed(rss('The new denim collection'),SOURCE,NOW),[])
        self.assertEqual(parse_feed(rss(date='Tue, 17 Nov 2026 12:00:00 GMT'),SOURCE,NOW),[])
        self.assertEqual(parse_feed(rss(date=''),SOURCE,NOW),[])
    def test_unsafe_url_and_foreign_domain_rejected(self):
        for value in ['javascript:alert(1)','http://example.org/a','https://evil.org/story','https://user:pass@example.org/story']:
            self.assertIsNone(safe_url(value,SOURCE))
    def test_markup_is_text_and_duplicates_collapse(self):
        item=parse_feed(rss('&lt;b&gt;New tights&lt;/b&gt;'),SOURCE,NOW)[0]
        self.assertEqual(item['title'],'New tights')
        self.assertEqual(len(merge_items([item,item],NOW)),1)
    def test_partial_failure_preserves_old_source(self):
        old=collect([SOURCE],{},lambda s:rss(),NOW)
        bad={**SOURCE,'id':'bad','url':'https://example.org/bad'}
        def fetch(s):
            if s['id']=='test': raise OSError('offline')
            return rss('Red tights','https://example.org/red')
        result=collect([SOURCE,bad],old,fetch,NOW)
        self.assertEqual(len(result['items']),2)
        self.assertEqual(result['sources'][0]['status'],'error')
    def test_total_failure_keeps_success_time_and_items(self):
        old=collect([SOURCE],{},lambda s:rss(),NOW)
        def fail(s): raise OSError('offline')
        result=collect([SOURCE],old,fail,NOW)
        self.assertEqual(result['lastSuccessfulAt'],old['lastSuccessfulAt'])
        self.assertEqual(result['items'],old['items'])
    def test_empty_valid_feed_counts_as_success(self):
        result=collect([SOURCE],{},lambda s:b'<rss><channel/></rss>',NOW)
        self.assertEqual(result['sources'][0]['status'],'ok')
        self.assertEqual(result['items'],[])
    def test_html_error_is_not_a_feed(self):
        with self.assertRaises(ValueError):parse_feed(b'<html><body>Error</body></html>',SOURCE,NOW)
    def test_aggregator_requires_allowed_publisher(self):
        source={**SOURCE,'site':'https://news.google.com','publishers':['example.org']}
        raw=rss('New tights - Test','https://news.google.com/rss/articles/abc').replace(b'</item>',b'<source url="https://example.org">Test</source></item>')
        item=parse_feed(raw,source,NOW)[0]
        self.assertEqual(item['title'],'New tights')
        self.assertEqual(item['via'],'Google News')
        self.assertEqual(parse_feed(raw.replace(b'https://example.org',b'https://evil.org'),source,NOW),[])
    def test_snapshot_failure_blocks_publish_except_initial_404(self):
        seed={'version':1,'items':[],'sources':[]}
        def offline(url):raise OSError('offline')
        with self.assertRaises(OSError):updater.restore_previous(seed,offline)
        with self.assertRaises(ValueError):updater.restore_previous(seed,lambda url:b'<html>error</html>')
        def missing(url):raise updater.FetchError(404)
        self.assertEqual(updater.restore_previous(seed,missing),seed)

if __name__=='__main__':unittest.main()
