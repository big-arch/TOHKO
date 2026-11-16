"""Video feed boundaries, source outage recovery, and catalog preservation."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from video_feed import FetchError, candidates, classify, collect, identity, verify

spec = importlib.util.spec_from_file_location("update_videos", ROOT / "scripts/update-videos.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)
NOW = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
CONFIG = json.loads((ROOT / "tights-guide/data/video-sources.json").read_text("utf-8"))
SOURCE = CONFIG["sources"][0]
ID = "abcdefghijk"


def feed(title="How to choose opaque tights", published="2026-11-15T10:00:00Z", link=None, channel=None):
    channel = channel or SOURCE["channelId"]
    return f'''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/">
      <yt:channelId>{channel}</yt:channelId><entry><yt:channelId>{channel}</yt:channelId>
      <yt:videoId>{ID}</yt:videoId><title>{title}</title><published>{published}</published>
      <link rel="alternate" href="{link or 'https://www.youtube.com/watch?v='+ID}"/>
      <media:group><media:description>How to find the right tights for your wardrobe.</media:description></media:group></entry></feed>'''.encode()


def embed(**changes):
    data = dict(type="video", title="How to choose opaque tights", author_name="CalzedoniaOfficial",
                author_url=SOURCE["authorUrls"][0], thumbnail_url="https://i.ytimg.com/vi/"+ID+"/hqdefault.jpg",
                thumbnail_width=480, thumbnail_height=360,
                html='<iframe src="https://www.youtube.com/embed/'+ID+'"></iframe>')
    data.update(changes)
    return json.dumps(data).encode()


def config():
    value = copy.deepcopy(CONFIG)
    value["sources"] = [copy.deepcopy(SOURCE)]
    return value


def store(video):
    return "assets/videos-new/" + video["id"] + ".jpg"


class FeedTests(unittest.TestCase):
    def test_date_from_feed_not_fetch_time(self):
        found = candidates(feed(), SOURCE, NOW, 540)
        self.assertEqual(found[0]["publishedAt"], "2026-11-15T10:00:00Z")
        self.assertEqual(found[0]["topics"], ["choice"])

    def test_missing_ambiguous_future_invalid_and_old_dates_are_rejected(self):
        for value in ("", "2026-11-15", "not-a-date", "2026-11-15T12:00:00", "2030-01-01T00:00:00Z", "2020-01-01T00:00:00Z"):
            with self.subTest(value=value):
                self.assertEqual(candidates(feed(published=value), SOURCE, NOW, 540), [])

    def test_timezone_normalized(self):
        self.assertEqual(candidates(feed(published="2026-11-15T13:00:00+03:00"), SOURCE, NOW, 540)[0]["publishedAt"], "2026-11-15T10:00:00Z")

    def test_unrelated_title_is_not_saved_due_to_channel_footer(self):
        self.assertEqual(candidates(feed(title="Winter jackets and shoes"), SOURCE, NOW, 540), [])
        self.assertEqual(classify("New bikini collection"), [])
        self.assertEqual(classify("Nude tights fetish compilation"), [])

    def test_identity_enforces_exact_official_domains(self):
        for url in ("https://www.youtube.com.evil.test/watch?v="+ID,
                    "https://www.youtube.com@evil.test/watch?v="+ID,
                    "http://www.youtube.com/watch?v="+ID,
                    "https://evil.test/embed/"+ID,
                    "https://player.vimeo.com/video/1224898418?h=private"):
            self.assertIsNone(identity(url), url)
        self.assertEqual(identity("https://youtu.be/"+ID)[1], ID)
        self.assertEqual(candidates(feed(link="https://evil.test/watch?v="+ID), SOURCE, NOW, 540), [])

    def test_channel_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            candidates(feed(channel="UC"+"x"*22), SOURCE, NOW, 540)

    def test_real_youtube_feed_omits_uc_at_root_but_not_in_entry(self):
        channel = SOURCE["channelId"].encode()
        raw = feed().replace(b'<yt:channelId>'+channel, b'<yt:channelId>'+channel[2:], 1)
        self.assertEqual(len(candidates(raw, SOURCE, NOW, 540)), 1)

    def test_entity_and_wrong_feed_rejected(self):
        for raw in (b'<feed/>', b'<!DOCTYPE feed><feed/>'):
            with self.assertRaises(ValueError):
                candidates(raw, SOURCE, NOW, 540)

    def test_oembed_rejects_foreign_author_host_or_wrong_video(self):
        candidate = candidates(feed(), SOURCE, NOW, 540)[0]
        for changes in ({"author_url": "https://www.youtube.com/@someone-else"},
                        {"html": '<iframe src="https://evil.test/embed/'+ID+'"></iframe>'},
                        {"html": '<iframe src="https://www.youtube.com/embed/xxxxxxxxxxx"></iframe>'},
                        {"html": '<iframe src="https://www.youtube.com/watch?v='+ID+'"></iframe>'},
                        {"thumbnail_url": "https://evil.test/preview.jpg"},
                        {"type": "link"}, {"title": "Beachwear summer campaign"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                verify(candidate, SOURCE, embed(**changes), NOW, 540)

    def test_html_is_stripped_from_display_metadata(self):
        candidate = candidates(feed(), SOURCE, NOW, 540)[0]
        video = verify(candidate, SOURCE, embed(title='<script>alert(1)</script>Opaque tights'), NOW, 540)
        self.assertEqual(video["title"], "Opaque tights")
        self.assertNotIn("html", video)
        self.assertEqual(video["language"], "original")

    def test_publisher_vimeo_date_and_author(self):
        source = CONFIG["sources"][1]
        raw = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Meet the makers</title><published>2026-09-07T12:00:00Z</published><link href="https://swedishstockings.com/blogs/journal/makers"/><content type="html">&lt;p&gt;Tights production and recycling&lt;/p&gt;&lt;iframe src="https://player.vimeo.com/video/1224898418"&gt;&lt;/iframe&gt;</content></entry></feed>'''
        candidate = candidates(raw, source, NOW, 540)[0]
        metadata = dict(type="video", title="split-banner-makers", author_name="Swedish Stockings",
                        author_url=source["authorUrls"][0], html='<iframe src="https://player.vimeo.com/video/1224898418"></iframe>',
                        thumbnail_url="https://i.vimeocdn.com/video/test.jpg", video_id=1224898418,
                        upload_date="2026-09-08 07:51:55", duration=23)
        video = verify(candidate, source, json.dumps(metadata), NOW, 540)
        self.assertEqual(video["publishedAt"], "2026-09-08")
        self.assertEqual(video["title"], "Meet the makers")
        self.assertEqual(video["originalTitle"], "split-banner-makers")
        metadata.pop("upload_date")
        with self.assertRaises(ValueError):
            verify(candidate, source, json.dumps(metadata), NOW, 540)

    def test_outage_preserves_catalog_and_backoff_then_recovers(self):
        original = [{"id": "snag-motion", "provider": "native", "title": "Existing", "originalTitle": "Existing", "author": "Snag"}]
        def fail(url):
            raise FetchError(429)
        first, state = collect(config(), original, {}, fail, store, NOW)
        self.assertEqual(first, original)
        self.assertEqual(state["sources"][0]["status"], "error")
        calls = []
        def unexpected(url):
            calls.append(url)
            raise AssertionError("backoff source must not be fetched")
        second, later = collect(config(), first, state, unexpected, store, NOW + timedelta(minutes=30))
        self.assertEqual(second, original)
        self.assertEqual(calls, [])
        def success(url):
            return feed() if "feeds/" in url else embed()
        third, recovered = collect(config(), second, later, success, store, NOW + timedelta(hours=3))
        self.assertEqual(third[0], original[0])
        self.assertEqual(third[1]["id"], ID)
        self.assertEqual(recovered["sources"][0]["failures"], 0)
        self.assertEqual(recovered["sources"][0]["status"], "ok")

    def test_oembed_unavailable_does_not_replace_originals(self):
        original = [{"id": "curated", "originalTitle": "Existing", "author": "Author"}]
        def fetch(url):
            if "feeds/" in url:
                return feed()
            raise FetchError(403)
        catalog, state = collect(config(), original, {}, fetch, store, NOW)
        self.assertEqual(catalog, original)
        self.assertEqual(state["added"], 0)
        self.assertEqual(state["sources"][0]["rejected"], 1)

    def test_dedup_prevents_repeat_network_verification(self):
        def fetch(url):
            return feed() if "feeds/" in url else embed()
        first, state = collect(config(), [], {}, fetch, store, NOW)
        calls = []
        def counted(url):
            calls.append(url)
            return feed()
        second, _ = collect(config(), first, state, counted, store, NOW + timedelta(hours=6))
        self.assertEqual(second, first)
        self.assertEqual(len(calls), 1)

    def test_deployed_restore_does_not_erase_local_curated_changes(self):
        seed = [{"id": "curated", "title": "Current edit"}]
        def fetch(url):
            if url.endswith("video-feed-state.json"):
                raise FetchError(404)
            return json.dumps([{"id": "curated", "title": "Old live title"}, {"id": "other", "title": "Live history"}]).encode()
        result, state = updater.restore_previous(seed, fetch)
        self.assertEqual(result[0]["title"], "Current edit")
        self.assertEqual(len(result), 2)
        self.assertEqual(state, {})
        with self.assertRaises(FetchError):
            updater.restore_previous(seed, lambda url: (_ for _ in ()).throw(FetchError(503)))

    def test_catalog_cap_keeps_newest_auto_entries_and_all_curated(self):
        fixed = {'id':'curated','title':'Original','author':'Author'}
        old = [dict(id=str(n),title=str(n),author='Author',addedBy='feed',publishedAt=f'2026-11-{n:02}') for n in range(1,5)]
        settings = config();settings['maxAutoVideos']=2
        catalog, _ = collect(settings,[fixed]+old,{},lambda url: feed(title='Unrelated jacket'),store,NOW)
        self.assertIn(fixed,catalog)
        self.assertEqual([x['id'] for x in catalog if x.get('addedBy')=='feed'],['4','3'])

    def test_max_new_limits_oembed_and_thumbnail_requests(self):
        settings=config();settings['maxNewPerRun']=1
        # Three distinct feed videos with no extra discovery pages.
        raw=feed();entry=raw[raw.index(b'<entry>'):raw.index(b'</entry>')+8]
        raw=raw.replace(b'</feed>',entry.replace(ID.encode(),b'xxxxxxxxxxx')+entry.replace(ID.encode(),b'yyyyyyyyyyy')+b'</feed>')
        calls=[];stored=[]
        def fetch(url):
            calls.append(url)
            return raw if 'feeds/' in url else embed()
        def thumbnail(video):
            stored.append(video['id']);return store(video)
        catalog,state=collect(settings,[],{},fetch,thumbnail,NOW)
        self.assertEqual(len(catalog),1)
        self.assertEqual(len(calls),2)
        self.assertEqual(stored,[ID])
        self.assertEqual(state['sources'][0]['candidates'],3)


if __name__ == "__main__":
    unittest.main()
