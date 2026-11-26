import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys
import tempfile
import unittest
from io import BytesIO

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from auto_content import allowed_url, canonical, collect, make_items, parse_feed, add_images, iso

NOW = datetime(2026, 11, 25, 12, tzinfo=timezone.utc)
SOURCE = {'id': 'a', 'name': 'Brand', 'kind': 'journal', 'format': 'feed', 'language': 'en',
          'url': 'https://example.com/journal.atom', 'pagePrefix': 'https://example.com/articles/',
          'include': '(?i)tights', 'imagePrefix': 'https://cdn.example.com/brand/', 'imagePattern': 'tights'}


def atom(title='Winter tights', url='https://example.com/articles/a', published='2026-11-24T10:00:00Z', body='A short lead.'):
    return (f'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>{title}</title>'
            f'<link href="{url}"/><published>{published}</published><content type="html"><![CDATA[{body}]]></content></entry></feed>').encode()


class Feeds(unittest.TestCase):
    def test_urls_reject_credentials_private_hosts_and_host_lookalikes(self):
        for u in ['http://example.com/articles/a', 'https://example.com.evil.org/articles/a',
                  'https://example.com@evil.org/articles/a', 'https://user@example.com/articles/a',
                  'https://127.0.0.1/articles/a', 'https://example.com:444/articles/a', 'javascript:alert(1)']:
            with self.subTest(url=u):
                self.assertFalse(allowed_url(u, [SOURCE['pagePrefix']]))
        self.assertTrue(allowed_url('https://example.com/articles/a', [SOURCE['pagePrefix']]))

    def test_atom_timezone_and_safe_plain_text(self):
        items = make_items(atom(published='2026-11-24T12:00:00+02:00',
                                body='<script>bad()</script><p>Text &amp; material.</p><img src="https://evil.org/tights.jpg">'), SOURCE, NOW)
        self.assertEqual(items[0]['publishedAt'], '2026-11-24T10:00:00Z')
        self.assertEqual(items[0]['excerpt'], 'Text & material.')
        self.assertNotIn('imageUrl', items[0])

    def test_rss_and_unknown_date_do_not_invent_publication(self):
        raw = b'<rss><channel><item><title>Winter tights</title><link>https://example.com/articles/a</link><description>Text</description></item></channel></rss>'
        self.assertIsNone(make_items(raw, SOURCE, NOW)[0]['publishedAt'])
        raw = raw.replace(b'<description>', b'<pubDate>Tue, 24 Nov 2026 10:00:00 +0000</pubDate><description>')
        self.assertEqual(make_items(raw, SOURCE, NOW)[0]['publishedAt'], '2026-11-24T10:00:00Z')

    def test_future_and_promotional_and_adult_entries_are_excluded(self):
        for raw in [atom(published='2027-12-01T00:00:00Z'), atom(title='Black Friday tights'),
                    atom(title='Crotchless tights'), atom(body='Fetish collection')]:
            self.assertEqual(make_items(raw, SOURCE, NOW), [])

    def test_shopify_filters_products_and_keeps_published_date(self):
        source = dict(SOURCE, kind='men', format='shopify', pagePrefix='https://example.com/products/')
        raw = json.dumps({'products': [{'title': '120D tights', 'handle': '120d', 'published_at': '2026-10-01T00:00:00Z'},
                                       {'title': 'Gift card', 'handle': 'gift'}, {'title': 'Intimacy tights', 'handle': 'intimacy'}]}).encode()
        items = make_items(raw, source, NOW)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['kind'], 'men')
        self.assertEqual(items[0]['publishedAt'], '2026-10-01T00:00:00Z')

    def test_duplicate_urls_and_tracking_do_not_create_duplicates(self):
        self.assertEqual(canonical('https://example.com/a?utm_source=x#y'), 'https://example.com/a')
        raw = atom().replace(b'</feed>', atom().split(b'<entry>')[1].replace(b'</feed>', b'').join([b'<entry>', b'</feed>']))
        self.assertEqual(len(make_items(raw, SOURCE, NOW)), 1)

    def test_invalid_xml_or_challenge_page_fails_closed(self):
        for raw in [b'<html>Please enable JavaScript</html>', b'<!DOCTYPE x><rss/>', b'<feed>']:
            with self.assertRaises(Exception):
                parse_feed(raw)

    def test_repeat_run_keeps_first_seen_and_publication_date(self):
        first = collect([SOURCE], {}, NOW, lambda *args: atom())
        again = collect([SOURCE], first, NOW + timedelta(days=1), lambda *args: atom())
        self.assertEqual(len(again['items']), 1)
        for key in ('firstSeenAt', 'lastChangedAt', 'publishedAt', 'id'):
            self.assertEqual(first['items'][0][key], again['items'][0][key])
        self.assertEqual(again['sources'][0]['newCount'], 0)
        self.assertNotEqual(first['checkedAt'], again['checkedAt'])

    def test_changed_entry_is_updated_not_duplicated(self):
        first = collect([SOURCE], {}, NOW, lambda *args: atom())
        again = collect([SOURCE], first, NOW + timedelta(days=1), lambda *args: atom(title='Blue winter tights'))
        self.assertEqual(len(again['items']), 1)
        self.assertEqual(first['items'][0]['firstSeenAt'], again['items'][0]['firstSeenAt'])
        self.assertNotEqual(first['items'][0]['lastChangedAt'], again['items'][0]['lastChangedAt'])

    def test_previously_allowed_entry_removed_when_now_excluded(self):
        first = collect([SOURCE], {}, NOW, lambda *args: atom())
        again = collect([SOURCE], first, NOW + timedelta(days=1), lambda *args: atom(title='Black Friday tights'))
        self.assertEqual(again['items'], [])

    def test_all_sources_failing_preserves_input_edition(self):
        first = collect([SOURCE], {}, NOW, lambda *args: atom())
        before = copy.deepcopy(first)
        def failed(*args): raise OSError('offline')
        with self.assertRaises(RuntimeError):
            collect([SOURCE], first, NOW + timedelta(days=1), failed)
        self.assertEqual(first, before)

    def test_partial_outage_keeps_previous_source(self):
        other = dict(SOURCE, id='b', url='https://second.com/journal.atom', pagePrefix='https://second.com/articles/')
        def fetcher(url, *args):
            return atom(url='https://second.com/articles/b') if 'second.com' in url else atom()
        first = collect([SOURCE, other], {}, NOW, fetcher)
        def partial(url, *args):
            if 'second.com' in url: raise OSError('offline')
            return atom()
        again = collect([SOURCE, other], first, NOW + timedelta(days=1), partial)
        self.assertEqual(len(again['items']), 2)
        self.assertEqual(again['sources'][1]['status'], 'error')
        self.assertEqual(again['sources'][1]['lastSuccessAt'], iso(NOW))

    def test_bad_new_page_does_not_enter_edition(self):
        def fetcher(url, *args):
            if url.endswith('.atom'): return atom()
            raise OSError('404')
        with self.assertRaises(RuntimeError): collect([SOURCE], {}, NOW, fetcher)

    def test_image_duplicate_and_mens_import_guard(self):
        from PIL import Image
        stream = BytesIO()
        Image.new('RGB', (400, 500), 'grey').save(stream, 'JPEG')
        data = collect([SOURCE], {}, NOW, lambda *args: atom(body='<img src="https://cdn.example.com/brand/tights.jpg">'))
        second = dict(data['items'][0], id='0123456789abcdef')
        male = dict(second, id='1234567890abcdef', kind='men')
        data['items'].extend([second, male])
        with tempfile.TemporaryDirectory() as directory:
            media = add_images(data, [], [SOURCE], Path(directory), lambda *args: stream.getvalue())
            self.assertEqual(len(media), 1)
            self.assertEqual(data['items'][0]['mediaId'], second['mediaId'])
            self.assertNotIn('mediaId', male)
            again = add_images(data, media, [SOURCE], Path(directory), lambda *args: stream.getvalue())
            self.assertEqual(len(again), 1)

    def test_non_image_response_does_not_enter_gallery(self):
        data = collect([SOURCE], {}, NOW, lambda *args: atom(body='<img src="https://cdn.example.com/brand/tights.jpg">'))
        with tempfile.TemporaryDirectory() as directory:
            media = add_images(data, [], [SOURCE], Path(directory), lambda *args: b'<html>error</html>')
            self.assertEqual(media, [])
            self.assertNotIn('mediaId', data['items'][0])

    def test_failed_replacement_keeps_existing_photograph(self):
        from PIL import Image
        stream = BytesIO()
        Image.new('RGB', (400, 500), 'grey').save(stream, 'JPEG')
        data = collect([SOURCE], {}, NOW, lambda *args: atom(body='<img src="https://cdn.example.com/brand/tights.jpg">'))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            media = add_images(data, [], [SOURCE], root, lambda *args: stream.getvalue())
            photo = media[0]
            data['items'][0]['imageUrl'] = 'https://cdn.example.com/brand/new-tights.jpg'
            data['items'][0].pop('mediaId')
            def offline(*args): raise OSError('offline')
            again = add_images(data, media, [SOURCE], root, offline)
            self.assertEqual(again[0]['contentHash'], photo['contentHash'])
            self.assertEqual(data['items'][0]['mediaId'], photo['id'])
            self.assertTrue((root / photo['image']).exists())

    def test_pruning_only_removes_expired_managed_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'assets/updates'
            folder.mkdir(parents=True)
            expired = folder / 'auto-0000000000000000.webp'
            manual = folder / 'manual.webp'
            expired.write_bytes(b'generated')
            manual.write_bytes(b'user asset')
            media = [{'id': f'auto-{i:016x}', 'origin': 'feed', 'publishedAt': iso(NOW)} for i in range(49)]
            items = [{'kind': 'journal', 'mediaId': m['id']} for m in media]
            kept = add_images({'items': items, 'checkedAt': iso(NOW)}, media, [], root)
            self.assertEqual(len(kept), 48)
            self.assertFalse(expired.exists())
            self.assertEqual(manual.read_bytes(), b'user asset')

    def test_expired_gallery_photo_survives_in_published_article(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ('assets/updates', 'assets/responsive', 'data'):
                (root / folder).mkdir(parents=True)
            original = root / 'assets/updates/auto-0000000000000000.webp'
            preview = root / 'assets/responsive/auto-0000000000000000-640.webp'
            original.write_bytes(b'published original'); preview.write_bytes(b'published preview')
            (root / 'data/free-articles.json').write_text(json.dumps({'items': [{
                'summary': 'Published introduction', 'sections': [{'heading': 'Facts'}],
                'illustration': {'src': original.relative_to(root).as_posix()}}]}), encoding='utf-8')
            media = [{'id': f'auto-{i:016x}', 'origin': 'feed', 'publishedAt': iso(NOW)} for i in range(49)]
            items = [{'kind': 'journal', 'mediaId': m['id']} for m in media]
            kept = add_images({'items': items, 'checkedAt': iso(NOW)}, media, [], root)
            self.assertEqual(len(kept), 48)
            self.assertTrue(original.exists())
            self.assertTrue(preview.exists())


if __name__ == '__main__':
    unittest.main()
