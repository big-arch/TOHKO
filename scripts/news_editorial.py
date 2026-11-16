"""Attach reviewed original TONKO articles without altering publication dates."""
import json
from pathlib import Path

FIELDS=('displayTitle','summary','sections','illustration','references','checked')

def apply_editorial(news, path=None):
    path=path or Path(__file__).resolve().parents[1]/'tights-guide/data/news-digests.json'
    digests=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    images_path=path.with_name('news-illustrations.json')
    images=json.loads(images_path.read_text(encoding='utf-8')) if images_path.exists() else {}
    for item in news.get('items',[]):
        if item['id'] in digests:
            item.pop('ai',None)
            digest=digests[item['id']]
            for key in FIELDS:
                item.pop(key,None)
                if key in digest:item[key]=digest[key]
        # A reviewed photo must not turn an AI summary into a manual editorial
        # or replace its text, date or attribution when the feed refreshes.
        if item['id'] in images:item['illustration']=dict(images[item['id']])
    return news
