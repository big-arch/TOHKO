"""Deterministic tests; never spend API tokens or access credentials."""
import copy,json,sys,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from news_ai import enrich,validate_result,APIError,parse_response,article_cover,preserve_generated
NOW=datetime(2026,11,16,12,tzinfo=timezone.utc)
SOURCE={'id':'example','site':'https://example.org','name':'Example'}
TEXT=' '.join('Исходный материал о новой коллекции колготок и разных вариантах оформления.' for _ in range(70))
def item(i='one'):return {'id':i,'title':'New tights','url':'https://example.org/'+i,'sourceId':'example','source':'Example','publishedAt':'2026-11-16T10:00:00Z','excerpt':'A short note.'}
def result():return {'usable':True,'displayTitle':'Новая коллекция колготок','summary':'Марка представила варианты оформления новой коллекции.', 'sections':[{'heading':'Детали коллекции','paragraphs':[' '.join('В публикации представлены особенности модели и объяснены различия между вариантами.' for _ in range(16))]}]}
def ask(i,t):return result()
def fetch(i):return TEXT
class AITests(unittest.TestCase):
    def test_api_request_keeps_key_out_of_payload_and_uses_bounded_output(self):
        from unittest.mock import patch,MagicMock
        from news_ai import request_summary
        response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps(result())}]}]}).encode()
        with patch('news_ai.urlopen',return_value=response) as opener:
            self.assertTrue(request_summary(item(),TEXT,'not-a-real-key')['usable'])
        request=opener.call_args.args[0];payload=json.loads(request.data)
        self.assertEqual(request.full_url,'https://api.openai.com/v1/responses')
        self.assertNotIn('not-a-real-key',request.data.decode())
        self.assertFalse(payload['store']);self.assertEqual(payload['max_output_tokens'],4000)
        self.assertEqual(payload['text']['format']['type'],'json_schema')
    def test_corrupt_cache_blocks_paid_requests(self):
        for bad in [None,-100,True,'3',11]:
            cache={'date':'2026-11-16','calls':bad,'records':{}}
            with self.assertRaises(ValueError):enrich({'items':[item()]},[SOURCE],cache,fetch,lambda *a:self.fail('No paid calls'),NOW)
    def test_corrupt_ready_fields_cannot_override_feed(self):
        cache={'date':'2026-11-16','calls':1,'records':{'one':{'status':'ready','at':'2026-11-16T10:00:00Z','fields':{'sections':'oops'}}}}
        with self.assertRaises(ValueError):enrich({'items':[item()]},[SOURCE],cache,fetch,ask,NOW)
    def test_cross_domain_redirect_rejected_before_request(self):
        from news_ai import SafeArticleRedirect
        from urllib.request import Request
        handler=SafeArticleRedirect(SOURCE)
        with self.assertRaises(ValueError):handler.redirect_request(Request('https://example.org/a'),None,302,'Found',{},'https://evil.org/article')
        req=handler.redirect_request(Request('https://example.org/a'),None,302,'Found',{},'https://www.example.org/article')
        self.assertEqual(req.full_url,'https://www.example.org/article')
    def test_ai_failure_does_not_block_rss_workflow(self):
        workflow=(Path(__file__).resolve().parents[1]/'.github/workflows/pages.yml').read_text(encoding='utf-8')
        for name in ['Restore generated summaries','Generate new on-site summaries','Save generated summaries and request counters']:
            stage=workflow.split('- name: '+name,1)[1].split('\n      - ',1)[0]
            self.assertIn('continue-on-error: true',stage,name)
        self.assertIn("steps.ai-cache.outcome == 'success'",workflow)
    def test_article_cover_must_come_from_its_publisher_not_a_logo(self):
        markup='<meta property="og:image" content="https://example.org/cover.jpg">'
        self.assertEqual(article_cover(markup,SOURCE,item())['src'],'https://example.org/cover.jpg')
        for replacement in ['https://evil.org/cover.jpg','https://example.org/logo.jpg','javascript:alert(1)']:
            self.assertIsNone(article_cover(markup.replace('https://example.org/cover.jpg',replacement),SOURCE,item()))
    def test_refresh_preserves_ai_body_and_publish_time(self):
        old={'items':[{**item(),**{k:v for k,v in result().items() if k!='usable'},'ai':{'model':'gpt-6-luna','generatedAt':'2026-11-16T10:00:00Z','sourceWords':700}}],'aiUsage':{'date':'2026-11-16','calls':3}}
        fresh={'items':[{**item(),'publishedAt':'2026-11-16T11:00:00Z'}]}
        preserve_generated(fresh,old)
        self.assertEqual(fresh['items'][0]['publishedAt'],'2026-11-16T11:00:00Z')
        self.assertEqual(fresh['items'][0]['sections'],old['items'][0]['sections'])
        self.assertEqual(fresh['aiUsage']['calls'],3)
    def test_once_only_and_persistent_cache_restores_after_failed_deploy(self):
        news={'items':[item()]};cache={};calls=[]
        enrich(news,[SOURCE],cache,fetch,lambda i,t:(calls.append(i['id']) or result()),NOW)
        self.assertEqual(calls,['one']);self.assertIn('ai',news['items'][0])
        old={'items':[item()]}
        enrich(old,[SOURCE],cache,fetch,lambda *a:self.fail('Repeated API call'),NOW+timedelta(minutes=15))
        self.assertIn('sections',old['items'][0]);self.assertEqual(old['items'][0]['publishedAt'],item()['publishedAt'])
    def test_editorial_and_google_aggregator_are_not_sent(self):
        manual={**item('manual'),'sections':[{'heading':'Our work','paragraphs':['Original text']}],'summary':'Original'}
        google={**item('google'),'via':'Google News'}
        news={'items':[manual,google]}
        enrich(news,[SOURCE],{},lambda *a:self.fail('No article fetch'),ask,NOW)
        self.assertEqual(news['items'][0]['summary'],'Original')
    def test_source_failure_keeps_feed_and_does_not_call_api(self):
        news={'items':[item()]}
        def fail(i):raise OSError('offline')
        enrich(news,[SOURCE],{},fail,lambda *a:self.fail('No API call'),NOW)
        self.assertNotIn('sections',news['items'][0]);self.assertEqual(news['items'][0]['excerpt'],'A short note.')
    def test_per_run_and_daily_limits(self):
        cache={};news={'items':[item(str(i)) for i in range(20)]};calls=[]
        fn=lambda i,t:(calls.append(i['id']) or result())
        for n in range(5):enrich(news,[SOURCE],cache,fetch,fn,NOW+timedelta(minutes=n*15))
        self.assertEqual(len(calls),10)
        self.assertEqual(cache['calls'],10)
    def test_auth_failure_stops_batch_without_losing_news(self):
        news={'items':[item('a'),item('b')]};calls=[]
        def fail(i,t):calls.append(i['id']);raise APIError(401)
        enrich(news,[SOURCE],{},fetch,fail,NOW)
        self.assertEqual(calls,['a']);self.assertEqual(len(news['items']),2)
    def test_short_body_does_not_get_invented_text(self):
        news={'items':[item()]}
        enrich(news,[SOURCE],{},lambda i:'Only a headline',lambda *a:self.fail('No API call'),NOW)
        self.assertNotIn('sections',news['items'][0])
    def test_unsafe_source_rejected_before_fetch(self):
        news={'items':[{**item(),'url':'https://evil.org/article'}]}
        enrich(news,[SOURCE],{},lambda *a:self.fail('No fetch'),ask,NOW)
    def test_refusal_incomplete_bad_schema_and_copy_rejected(self):
        for raw in [{'status':'incomplete','output':[]},{'status':'completed','output':[{'content':[{'type':'refusal','refusal':'No'}]}]}]:
            with self.assertRaises(ValueError):parse_response(raw)
        for change in [{'usable':False},{'summary':'<script>x</script>'},{'sections':[]},{'displayTitle':'https://evil.org'}]:
            with self.assertRaises(ValueError):validate_result({**result(),**change},TEXT)
        with self.assertRaises(ValueError):validate_result(result(),' '.join(result()['sections'][0]['paragraphs'])*8)
    def test_output_text_parsing(self):
        raw={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(result())}]}]}
        self.assertTrue(parse_response(raw)['usable'])
if __name__=='__main__':unittest.main()
