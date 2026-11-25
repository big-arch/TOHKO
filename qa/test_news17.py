"""Publication dates, chronology and seven-day badges; entirely offline."""
import json
import re
import runpy
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from news_render import (is_new_publication, newest_publications, publication_markup,
                         publication_time, refresh_publication_badges, story)

NOW = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)


class PublicationDateTests(unittest.TestCase):
    def test_only_explicit_valid_publication_dates_are_recognized(self):
        for bad in (None, '', 0, 'not a date', '2026-02-30', '2026-11-17T12:00:00',
                    '2026-11-17T24:00:00Z', '2026-11-17T24:00Z',
                    '2026-11-17T12:60Z', '2026-11-17T12:00:60Z',
                    '2026-11-17T12:00:00+01:99', '2026-11-17T12:00:00+24:00', '0000-01-01'):
            with self.subTest(bad=bad):
                self.assertIsNone(publication_time(bad))
                self.assertNotIn('<time', publication_markup(bad, NOW))
                self.assertIn('Дата публикации не указана', publication_markup(bad, NOW))
        self.assertEqual(publication_time('2026-11-17'), NOW.replace(hour=0))
        self.assertEqual(publication_time('2026-11-17T15:00:00+03:00'), NOW)
        self.assertEqual(publication_time('2026-11-17T15:00+03:00'), NOW)

    def test_seven_day_window_excludes_future_and_exact_expiry(self):
        for delta, expected in ((timedelta(seconds=1), False), (timedelta(0), True),
                                (-timedelta(days=7)+timedelta(milliseconds=1), True),
                                (-timedelta(days=7), False), (-timedelta(days=8), False)):
            value = (NOW + delta).isoformat()
            with self.subTest(delta=delta):
                self.assertEqual(is_new_publication(value, NOW), expected)
                self.assertEqual(' hidden' not in publication_markup(value, NOW), expected)

    def test_chronology_ignores_check_import_and_generation_times(self):
        items = [
            {'id':'unknown', 'checkedAt':NOW.isoformat()},
            {'id':'old', 'publishedAt':'2025-01-01', 'importAt':NOW.isoformat()},
            {'id':'tie-a', 'publishedAt':'2026-11-16T12:00:00Z'},
            {'id':'invalid', 'publishedAt':'2026-02-30', 'checkedAt':NOW.isoformat()},
            {'id':'new', 'publishedAt':'2026-11-17T00:00:00Z', 'ai':{'generatedAt':'2025-01-01'}},
            {'id':'tie-b', 'publishedAt':'2026-11-16T15:00:00+03:00'},
        ]
        before = json.dumps(items)
        self.assertEqual([i['id'] for i in newest_publications(items)], ['new','tie-a','tie-b','old','unknown','invalid'])
        self.assertEqual(json.dumps(items), before)

    def test_server_markup_has_accessible_time_and_escapes_invalid_input(self):
        rendered = publication_markup('2026-11-16T07:00:00Z', NOW)
        self.assertIn('<time datetime="2026-11-16T07:00:00Z"', rendered)
        self.assertIn('aria-label="Дата публикации: 16 ноября 2026"', rendered)
        self.assertNotIn('<img', publication_markup('<img src=x onerror=alert(1)>', NOW))

    def test_offline_build_retires_static_badges_without_touching_dates(self):
        fresh = publication_markup('2026-11-15', NOW)
        old = refresh_publication_badges(fresh, NOW + timedelta(days=8))
        self.assertIn(' hidden>Новое', old)
        self.assertIn('datetime="2026-11-15"', old)
        self.assertEqual(refresh_publication_badges(old, NOW + timedelta(days=8)), old)
        self.assertEqual(refresh_publication_badges(old, NOW), fresh)

    def test_static_reader_uses_time_and_handles_missing_date(self):
        source = json.loads((ROOT/'tights-guide/data/news.json').read_text('utf-8'))
        item = next(dict(i) for i in source['items'] if i.get('sections'))
        self.assertIn('<time datetime="'+item['publishedAt']+'"', story(item))
        item.pop('publishedAt')
        self.assertIn('Дата публикации не указана', story(item))

    def test_home_and_full_reader_builder_sort_unsorted_input_without_redating(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root/'scripts'; scripts.mkdir()
            site = root/'tights-guide'; (site/'data').mkdir(parents=True)
            shutil.copy2(ROOT/'scripts/build-home-news.py', scripts/'build-home-news.py')
            shutil.copy2(ROOT/'tights-guide/news.js', site/'news.js')
            for name in ('news.json','editorial-media.json','packaging.json'):
                shutil.copy2(ROOT/'tights-guide/data'/name, site/'data'/name)
            source = json.loads((site/'data/news.json').read_text('utf-8'))
            source['items'].reverse()
            dates = {i['id']:i.get('publishedAt') for i in source['items']}
            (site/'data/news.json').write_text(json.dumps(source, ensure_ascii=False), encoding='utf-8')
            (site/'index.html').write_text('<html><head><title>ТОНКО</title></head><body><main><!-- experience-home --></main></body></html>', encoding='utf-8')
            runpy.run_path(str(scripts/'build-home-news.py'))
            home = (site/'index.html').read_text('utf-8')
            full = (site/'news.html').read_text('utf-8')
            expected = [i['id'] for i in newest_publications(source['items']) if i.get('sections')]
            self.assertEqual(re.findall(r'data-news-id="([^"]+)"', home), expected[:6])
            self.assertEqual(re.findall(r'id="story-([^"]+)"', full), expected)
            self.assertIn('publication-dates.js?v=20261117-17', full)
            after = json.loads((site/'data/news.json').read_text('utf-8'))
            self.assertEqual({i['id']:i.get('publishedAt') for i in after['items']}, dates)
            runpy.run_path(str(scripts/'build-home-news.py'))
            self.assertEqual((site/'index.html').read_text('utf-8'), home)

    def test_first_edition_has_documented_dates_in_metadata(self):
        text = (ROOT/'tights-guide/data/journal.js').read_text('utf-8')
        items = json.loads(text.split('=',1)[1].strip().rstrip(';'))
        self.assertEqual(len(items), 6)
        for item in items:
            self.assertEqual(item['publishedAt'], '2026-11-15')
            self.assertIn('a84eb33', item['publicationDateSource'])

    def test_editorial_rebuild_keeps_dates_and_handles_a_new_undated_story(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); scripts = root/'scripts'; scripts.mkdir()
            site = root/'tights-guide'; (site/'data').mkdir(parents=True)
            shutil.copy2(ROOT/'scripts/build-experience.py', scripts/'build-experience.py')
            for path in (ROOT/'tights-guide').glob('*.html'):
                shutil.copy2(path, site/path.name)
            shutil.copy2(ROOT/'tights-guide/data/editorial-media.json', site/'data/editorial-media.json')
            import copy
            import story_content
            original = copy.deepcopy(story_content.STORIES)
            # An unlisted future article must not acquire the first issue's date.
            undated = copy.deepcopy(original[0]); undated['id']='undated-regression'
            undated.pop('publishedAt',None); undated.pop('publicationDateSource',None)
            try:
                story_content.STORIES = [undated,*copy.deepcopy(original)]
                runpy.run_path(str(scripts/'build-experience.py'))
                journal = (site/'journal.html').read_text('utf-8')
                self.assertEqual(re.findall(r'data-story="([^"]+)"',journal),[i['id'] for i in original]+['undated-regression'])
                self.assertIn('Дата публикации не указана',(site/'read-undated-regression.html').read_text('utf-8'))
                self.assertEqual(journal.count('publication-dates.js'),1)
                self.assertEqual(journal.count('experience.js?v=20261117-17'),1)
                index = (site/'data/journal.js').read_text('utf-8')
                runpy.run_path(str(scripts/'build-experience.py'))
                self.assertEqual((site/'data/journal.js').read_text('utf-8'),index)
            finally:
                story_content.STORIES = original


if __name__ == '__main__':
    unittest.main()
