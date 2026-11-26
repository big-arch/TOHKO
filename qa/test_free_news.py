from pathlib import Path
from unittest.mock import patch
import sys
import unittest
import copy

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import free_news as free

SOURCE={'id':'example','site':'https://example.org','name':'Example'}


class FreeNews(unittest.TestCase):
    def test_feed_uses_full_content_not_a_teaser(self):
        body='Useful source information about tights and construction. '*40
        xml=f'<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item><title>Tights</title><link>https://example.org/a</link><description>Only a headline.</description><content:encoded><![CDATA[<p>{body}</p>]]></content:encoded></item></channel></rss>'.encode()
        data=free.complete_feed(xml,SOURCE)
        self.assertEqual(data['https://example.org/a']['text'],body.strip())
        self.assertEqual(free.complete_feed(xml.replace(body.encode(),b'short'),SOURCE),{})

    def test_feed_dtd_and_foreign_links_rejected(self):
        with self.assertRaises(ValueError):free.complete_feed(b'<!DOCTYPE rss><rss/>',SOURCE)
        xml=('<rss><channel><item><link>https://other.org/a</link><content>'+('word '*200)+'</content></item></channel></rss>').encode()
        self.assertEqual(free.complete_feed(xml,SOURCE),{})

    def test_paid_and_cloud_endpoints_rejected_before_network(self):
        with patch.object(free,'urlopen') as network:
            for endpoint,model in [('https://api.openai.com','qwen3:4b'),('http://localhost:11434','qwen-cloud'),('http://user:pass@localhost','qwen3:4b')]:
                with self.assertRaises(ValueError):free.ask_local({},'',model,endpoint)
            network.assert_not_called()

    def test_repeated_or_unsupported_claims_are_rejected(self):
        fields={'displayTitle':'Как устроены тонкие колготки','summary':'Этот русский текст описывает фактуру и посадку изделия по данным источника.',
                'sections':[{'heading':'Конструкция','paragraphs':['Подробное описание устройства изделия объясняет особенности его конструкции без новых обещаний.']} ]}
        with patch.object(free,'validate_result',return_value=fields):
            fields['sections'][0]['paragraphs']=[fields['summary']]
            with self.assertRaisesRegex(ValueError,'Repeated'):free.validate({},'source')
            fields['sections'][0]['paragraphs']=['Эта модель имеет плотность 999 DEN и совершенно другую структуру полотна.']
            with self.assertRaisesRegex(ValueError,'numerical'):free.validate({},'source 20 DEN')

    def test_unreadable_records_do_not_replace_ready_editions(self):
        original={'id':'one','summary':'Existing complete introduction '*6,'sections':[{'heading':'Facts','paragraphs':['Existing independently prepared text. '*20]}]}
        news={'items':[original]};before=copy.deepcopy(original)
        free.apply_saved(news,{'items':[{'id':'one','title':'Bad incomplete overwrite'}]})
        self.assertEqual(news['items'][0]['summary'],before['summary'])

    def test_mixed_alphabet_translation_is_not_published(self):
        fields={'displayTitle':'Подкolanówki на первом плане','summary':'Русское описание новой коллекции колготок.',
                'sections':[{'heading':'Стиль','paragraphs':['Подробное описание нового изделия из коллекции.']} ]}
        with patch.object(free,'validate_result',return_value=fields):
            with self.assertRaisesRegex(ValueError,'Mixed alphabets'):free.validate({},'source')

    def test_complete_review_merges_and_keeps_original_date(self):
        source={'id':'example','site':'https://example.org','name':'Example'}
        article={'id':'one','url':'https://example.org/a','publisherUrl':'https://example.org/a',
                 'sourceId':'example','source':'Example','publishedAt':'2026-11-01T00:00:00Z','language':'en',
                 'displayTitle':'Новый русский обзор конструкции колготок','summary':'Подробное вступление к самостоятельному обзору устройства и применения изделия.',
                 'sections':[{'heading':'Особенности конструкции','paragraphs':['Факты о конструкции изделия объяснены в отдельном русском обзоре. '*14]}],
                 'localSummary':{'model':'local','generatedAt':'2026-11-26T00:00:00Z'}}
        with patch.object(free,'sources',return_value=[source]):
            result=free.apply_saved({'items':[]},{'items':[article]})
        self.assertEqual(len(result['items']),1)
        self.assertEqual(result['items'][0]['publishedAt'],'2026-11-01T00:00:00Z')
        self.assertEqual(result['items'][0]['summary'],article['summary'])

    def test_photo_matches_source_and_preserves_actual_credit(self):
        media=[{'id':'a','source':'https://example.org/a','image':'assets/updates/a.webp','width':1200,'height':900,'alt':'Black tights','author':'Brand'}]
        image=free.illustration({'url':'https://example.org/a','title':'Collection'},media)
        self.assertEqual(image['source'],'https://example.org/a')
        self.assertIn('из этой публикации',image['caption'])
        self.assertIsNone(free.illustration({'url':'https://example.org/b','title':'Unrelated event'},media))

    def test_workflow_has_no_paid_secrets_and_requires_public_repository(self):
        text=(free.ROOT/'.github/workflows/free-articles.yml').read_text(encoding='utf8')
        self.assertNotIn('secrets.',text)
        self.assertIn('repository.private == false',text)
        self.assertIn('127.0.0.1',text)
        self.assertIn('sha256sum --check',text)
        self.assertIn('uses: ./.github/workflows/pages.yml',text)


if __name__=='__main__':unittest.main()
