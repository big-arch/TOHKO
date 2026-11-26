"""Publication and relevance invariants for the visual guide and living editorials."""
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
import copy
import importlib.util
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
spec = importlib.util.spec_from_file_location('editorial_updates', ROOT/'scripts/build-editorial-updates.py')
updates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updates)


def item(key='one', title='Матовые колготки: как меняется блеск', date='2026-11-20T12:00:00Z'):
    return {'id': key, 'publisherUrl': 'https://example.org/'+key, 'displayTitle': title,
            'publishedAt': date, 'summary': 'В этом материале разобраны особенности изделия и даны примеры из источника. '*3,
            'sections': [{'heading': 'Наблюдение', 'paragraphs': ['Описание проверенных деталей материала помогает сопоставить свойства разных изделий. '*8]}],
            'illustration': {'src': 'assets/example.webp'}}


class EditorialSelection(unittest.TestCase):
    def test_only_complete_russian_illustrated_articles_are_selected(self):
        good = item()
        no_body = item('no-body'); no_body['sections'] = []
        no_photo = item('no-photo'); no_photo.pop('illustration')
        external_photo = item('external'); external_photo['illustration']['src'] = 'https://example.org/p.jpg'
        english = item('english', 'Matte and shiny tights')
        self.assertEqual([i['id'] for i in updates.select('light', [no_body, no_photo, external_photo, english, good])], ['one'])

    def test_each_article_matches_its_editorial_topic(self):
        titles = {'light': 'Матовые колготки и блеск', 'patterns': 'Кружево и геометрия рисунка',
                  'construction': 'Посадка и пояс', 'product-card': 'Размер и состав модели',
                  'making': 'Переработка сырья на производстве', 'archive': 'История и основатель компании'}
        for topic, title in titles.items():
            with self.subTest(topic=topic):
                self.assertEqual(len(updates.select(topic, [item(title=title)])), 1)
                self.assertEqual(updates.select(topic, [item(title='Новая публикация')]), [])

    def test_decorative_crystals_are_not_manufacturing_news(self):
        self.assertEqual(updates.select('making', [item(title='Колготки и кристаллы для праздничного образа')]), [])

    def test_newest_three_and_duplicate_source(self):
        data = [item(str(n), date=f'2026-11-{n:02}T00:00:00Z') for n in range(10, 16)]
        data.append(copy.deepcopy(data[-1]))
        self.assertEqual([i['id'] for i in updates.select('light', data)], ['15', '14', '13'])

    def test_selection_never_edits_source_articles(self):
        data = [item()]; before = copy.deepcopy(data)
        updates.select('light', data)
        self.assertEqual(data, before)

    def test_addition_date_uses_actual_edit_instead_of_build_time(self):
        review = item(); review['localSummary'] = {'generatedAt': '2026-11-27T10:00:00Z'}
        with patch.object(updates, 'datetime') as clock:
            clock.fromisoformat.side_effect = datetime.fromisoformat
            clock.now.return_value = datetime(2026, 12, 20, tzinfo=timezone.utc)
            self.assertEqual(updates.addition_date([review]), '2026-11-27')
            self.assertEqual(updates.addition_date([]), updates.BASE_ADDITION)

    def test_review_date_respects_timezone_and_rejects_future(self):
        review = item(); review['localSummary'] = {'editorialReviewAt': '2026-11-28T01:30:00+03:00'}
        future = item('future'); future['localSummary'] = {'generatedAt': '2099-01-01T00:00:00Z'}
        with patch.object(updates, 'datetime') as clock:
            clock.fromisoformat.side_effect = datetime.fromisoformat
            clock.now.return_value = datetime(2026, 12, 20, tzinfo=timezone.utc)
            self.assertEqual(updates.addition_date([review, future]), '2026-11-27')

    def test_authored_text_remains_when_no_matching_update_exists(self):
        self.assertEqual(updates.select('making', []), [])
        self.assertEqual(len(updates.TOPICS['making'][2]), 3)


class PublishedGuide(unittest.TestCase):
    def test_every_comparison_uses_a_real_local_photo(self):
        text = (ROOT/'tights-guide/guide.html').read_text(encoding='utf-8')
        import re
        data = json.loads(re.search(r'id="guide-studio-data">(.*?)</script>', text).group(1))
        self.assertEqual(len(data['photos']), 10)
        for key, photo in data['photos'].items():
            with self.subTest(photo=key):
                self.assertTrue((ROOT/'tights-guide'/photo['image']).is_file())
                self.assertTrue(photo['source'].startswith('https://') or key=='campaign-red')

    def test_loops_load_only_on_request_and_have_offline_posters(self):
        from html.parser import HTMLParser
        class Videos(HTMLParser):
            def __init__(self): super().__init__(); self.items = []
            def handle_starttag(self, tag, attrs):
                if tag == 'video': self.items.append(dict(attrs))
        parser = Videos(); parser.feed((ROOT/'tights-guide/guide.html').read_text(encoding='utf-8'))
        self.assertEqual(len(parser.items), 2)
        for v in parser.items:
            self.assertNotIn('src', v)
            self.assertNotIn('autoplay', v)
            self.assertIn('controls', v)
            self.assertEqual(v['preload'], 'none')
            self.assertTrue((ROOT/'tights-guide'/v['poster']).is_file())


if __name__ == '__main__': unittest.main()
