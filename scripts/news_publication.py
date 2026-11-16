"""A feed discovery is not an article: one publication gate for every renderer."""
import re
from news_feed import iso

def is_ready(item):
    if not isinstance(item.get('summary'),str) or len(item['summary'])<30:return False
    sections=item.get('sections')
    if not isinstance(sections,list) or not sections:return False
    paragraphs=[]
    for section in sections:
        if not isinstance(section,dict) or not isinstance(section.get('heading'),str):return False
        body=section.get('paragraphs')
        if not isinstance(body,list) or not body or not all(isinstance(p,str) and len(p)>=30 for p in body):return False
        paragraphs.extend(body)
    return len(re.findall(r'\w+',item['summary']+' '+' '.join(paragraphs)))>=65

def sync_publication(news,now=None):
    counts={'ready':0,'pending':0,'failed':0}
    for item in news.get('items',[]):
        if is_ready(item):
            state={'status':'ready'}
            checked=item.get('checked') or item.get('ai',{}).get('generatedAt')
            if checked:state['checkedAt']=checked
            item['publication']=state
        else:
            state=item.get('publication',{})
            if not isinstance(state,dict) or state.get('status') not in ('pending','failed'):
                state={'status':'pending','reason':'awaiting_source','attempts':0,'fetchAttempts':0}
                if now:state['queuedAt']=iso(now)
                item['publication']=state
        counts[state['status']]+=1
    news['queue']=counts
    return counts
