"""Attach reviewed original TONKO articles without altering publication dates."""
import json
from pathlib import Path

FIELDS=('displayTitle','summary','sections','illustration','references','checked')

def apply_editorial(news, path=None):
    path=path or Path(__file__).resolve().parents[1]/'tights-guide/data/news-digests.json'
    digests=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    for item in news.get('items',[]):
        if item['id'] in digests:
            digest=digests[item['id']]
            for key in FIELDS:
                item.pop(key,None)
                if key in digest:item[key]=digest[key]
    return news
