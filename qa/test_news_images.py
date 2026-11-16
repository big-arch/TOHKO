import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from news_ai import request_summary,article_cover,enrich,MAX_OUTPUT_TOKENS
from news_images import allowed_image,reviewed_photo,ImageRedirect
from test_news_ai import item,result,TEXT,NOW,SOURCE
from urllib.request import Request

class ImageTests(unittest.TestCase):
    def test_hosts_and_redirects_remain_publisher_only(self):
        self.assertTrue(allowed_image('https://example.org/photo.jpg',SOURCE))
        for url in ['http://example.org/x.jpg','https://example.org.evil.com/x.jpg','https://user:pass@example.org/x.jpg','https://127.0.0.1/x.jpg','https://example.org:9000/x.jpg']:
            self.assertFalse(allowed_image(url,SOURCE))
        with self.assertRaises(ValueError):ImageRedirect(SOURCE).redirect_request(Request('https://example.org/a'),None,302,'Found',{},'https://evil.org/x.jpg')
    def test_winter_cover_can_only_be_a_candidate_until_visual_review(self):
        story={**item(),'title':'Winter tights'};raw='<meta property="og:image" content="https://example.org/photo.jpg">'
        self.assertIsNone(article_cover(raw,SOURCE,story))
        candidate=article_cover(raw,SOURCE,story,allow_seasonal=True)
        story['_coverCandidate']=candidate
        self.assertIsNone(reviewed_photo(story,{'photoSuitable':True,'photoAlt':'Зимний образ с пальто.'}))
        story['_imageInput']='data:image/jpeg;base64,test'
        self.assertIsNone(reviewed_photo(story,{'photoSuitable':False,'photoAlt':''}))
        self.assertEqual(reviewed_photo(story,{'photoSuitable':True,'photoAlt':'Зимний образ с пальто.'})['src'],candidate['src'])
        self.assertIsNone(reviewed_photo(story,{'photoSuitable':True,'photoAlt':'<script>test</script>'}))
    def test_vision_is_part_of_one_bounded_request(self):
        response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps(result())}]}]}).encode()
        story={**item(),'_imageInput':'data:image/jpeg;base64,test'}
        with patch('news_ai.urlopen',return_value=response) as opener:request_summary(story,TEXT,'fake-test-key')
        self.assertEqual(opener.call_count,1)
        payload=json.loads(opener.call_args.args[0].data)
        self.assertFalse(payload['store']);self.assertEqual(payload['max_output_tokens'],MAX_OUTPUT_TOKENS)
        self.assertEqual(payload['input'][0]['content'][1]['type'],'input_image')
        self.assertIn('photoSuitable',payload['text']['format']['schema']['required'])
        self.assertNotIn('fake-test-key',json.dumps(payload))
    def test_image_rejection_preserves_article_without_misleading_photo(self):
        for suitable in (False,True):
            story={**item(),'_coverCandidate':{'src':'https://example.org/photo.jpg','source':'https://example.org/one'},'_imageInput':'data:image/jpeg;base64,test'}
            data={'items':[story]};cache={}
            enrich(data,[SOURCE],cache,lambda i:TEXT,lambda i,t:{**result(),'photoSuitable':suitable,'photoAlt':'Человек в пальто и высоких сапогах.'},NOW)
            self.assertEqual(story['publication']['status'],'ready')
            self.assertEqual('illustration' in story,suitable)
            self.assertNotIn('_imageInput',json.dumps(cache))
            self.assertEqual(cache['calls'],1)

if __name__=='__main__':unittest.main()
