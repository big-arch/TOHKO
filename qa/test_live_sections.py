from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('live_sections', ROOT / 'scripts/build-live-sections.py')
live = importlib.util.module_from_spec(spec)
spec.loader.exec_module(live)


def item(id='one', **extra):
    return dict(id=id, title='Tights for men', source='NYLO', sourceId='nylo',
                url='https://nylo.us/blogs/journal/'+id, excerpt='A short lead for readers.',
                publishedAt='2026-11-24T12:00:00Z', language='en', **extra)


class LiveSections(unittest.TestCase):
    def test_pending_discovery_is_not_published_as_an_external_article(self):
        source=item()
        data=live.prepare({'items':[source]}, {}, [])
        self.assertEqual(data['items'],[])

    def test_existing_full_article_wins_dedup_and_keeps_on_site_reading(self):
        original=item(summary='A complete introduction with enough detail for readers.' * 5,
                      sections=[{'heading':'Details','paragraphs':['A real paragraph containing useful source facts and explanations. ' * 10]}])
        extra={'id':'duplicate','url':original['url'],'title':'Duplicate','sourceName':'NYLO','sourceId':'nylo',
               'language':'en','excerpt':'Lead','publishedAt':original['publishedAt']}
        data=live.prepare({'items':[original]}, {'items':[extra]}, [])
        self.assertEqual(len(data['items']),1)
        self.assertTrue(data['items'][0]['ready'])
        self.assertEqual(data['items'][0]['url'],'news.html#story-one')

    def test_women_does_not_match_men_and_unsafe_links_are_rejected(self):
        source=item(summary='A complete introduction with enough detail for readers.'*5,sections=[{'heading':'Details','paragraphs':['A detailed article about a fabric and a pair of tights. '*10]}]);source.update(title="Women's tights",sourceId='brand')
        malicious=item('bad');malicious['url']='javascript:alert(1)'
        data=live.prepare({'items':[source,malicious]}, {}, [])
        self.assertEqual(len(data['items']),1)
        self.assertFalse(data['items'][0]['men'])

    def test_same_title_from_aggregator_is_not_a_second_article(self):
        direct=item(summary='A complete introduction with enough detail for readers.'*5,sections=[{'heading':'Details','paragraphs':['A detailed article about a fabric and a pair of tights. '*10]}])
        google=item('two');google['url']='https://news.google.com/articles/two'
        data=live.prepare({'items':[direct,google]}, {}, [])
        self.assertEqual(len(data['items']),1)

    def test_unprepared_google_redirect_is_not_a_reading_destination(self):
        google=item();google['url']='https://news.google.com/articles/one'
        data=live.prepare({'items':[google]}, {}, [])
        self.assertEqual(data['items'],[])

    def test_untrusted_titles_are_escaped_and_source_excerpt_is_bounded(self):
        source=item(summary='word '*90,sections=[{'heading':'Details','paragraphs':['A detailed article about a fabric and a pair of tights. '*10]}]);source['title']='<img src=x onerror=alert(1)>'
        data=live.prepare({'items':[source]}, {}, [])
        text=live.render_item(data['items'][0])
        self.assertIn('&lt;img',text)
        self.assertNotIn('<img src=x',text)
        self.assertLessEqual(len(data['items'][0]['excerpt'].split()),35)

    def test_optional_photo_stage_does_not_replace_curated_images(self):
        data=live.prepare({'items':[item()]}, {}, [{'id':'manual','origin':'user'}])
        self.assertEqual(data['photos'],[])
        self.assertEqual(data['items'],[])

    def test_pipeline_checks_built_data_and_no_paid_news_stage(self):
        workflow=(ROOT/'.github/workflows/pages.yml').read_text(encoding='utf-8')
        self.assertLess(workflow.index('python scripts/build-videos.py'),workflow.index('- name: Verify content and assistant'))
        self.assertIn("OPENAI_NEWS_ENABLED: 'false'",workflow)
        self.assertNotIn('secrets.OPENAI_API_KEY',workflow)
        self.assertIn('python scripts/build-live-sections.py',workflow)

    def test_bot_photo_commit_is_followed_by_explicit_publication(self):
        workflow=(ROOT/'.github/workflows/publisher-photos.yml').read_text(encoding='utf-8')
        self.assertIn("cron: '17 6 * * *'",workflow)
        self.assertIn('needs: collect',workflow)
        self.assertIn('uses: ./.github/workflows/pages.yml',workflow)
        self.assertNotIn('--force',workflow)
        self.assertNotIn('secrets.',workflow)


if __name__=='__main__':unittest.main()
