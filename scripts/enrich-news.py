"""Repair covers and generate bounded summaries. Images never require an API key."""
import json,os
from datetime import datetime,timezone
from pathlib import Path
from news_ai import enrich,extract_article,request_summary,article_cover,validate_cache,fetch_article_url,backfill_covers

ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'tights-guide/data'
def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)

def main():
    news=json.loads((DATA/'news.json').read_text(encoding='utf-8'))
    sources=json.loads((DATA/'news-sources.json').read_text(encoding='utf-8'))
    covers=backfill_covers(news,sources)
    if covers['added']:atomic(DATA/'news.json',news)
    print('Article covers:',json.dumps(covers))
    key=os.environ.get('OPENAI_API_KEY','').strip()
    if not key or os.environ.get('OPENAI_NEWS_ENABLED','true').lower()!='true':
        print('AI summaries disabled or OPENAI_API_KEY is absent; RSS news preserved.');return
    cache_path=ROOT/'.cache/news-ai-cache.json'
    try:
        cache=json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
        validate_cache(cache)
    except (OSError,ValueError):
        # A corrupt request ledger must not reset quota and cause paid reprocessing.
        print('::warning::AI cache unavailable; skipping paid requests and preserving news.');return
    source_map={s['id']:s for s in sources}
    def fetch_article(item):
        raw=fetch_article_url(item['url'],source_map[item['sourceId']]);text=extract_article(raw)
        if not item.get('illustration'):
            photo=article_cover(raw,source_map[item['sourceId']],item)
            if photo:item['illustration']=photo
        return text
    stats=enrich(news,sources,cache,fetch_article,
        lambda item,text:request_summary(item,text,key),datetime.now(timezone.utc),lambda:atomic(cache_path,cache))
    atomic(DATA/'news.json',news)
    print('AI summaries:',json.dumps(stats,ensure_ascii=True))
    if stats['apiStatus'] is not None:print('::warning::OpenAI request failed (HTTP '+str(stats['apiStatus'])+'); existing news retained.')

if __name__=='__main__':
    try:main()
    except Exception as error:
        # Keep the already refreshed RSS snapshot and never print secret-bearing errors.
        print('::warning::AI stage skipped ('+type(error).__name__+'); current RSS news preserved.')
