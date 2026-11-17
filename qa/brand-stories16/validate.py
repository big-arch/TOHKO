"""Focused data/media validation; does not change production content."""
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT/'tights-guide'
QA = Path(__file__).resolve().parent
sys.path.insert(0,r'C:\Users\Артур\Documents\CODEX_сайт_ТОНКО\.cache\pillow-runtime')
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
data=json.loads((SITE/'data/brand-stories.json').read_text(encoding='utf-8'))
packages=json.loads((SITE/'data/packaging.json').read_text(encoding='utf-8'))
archive_brands={x['brand'] for x in packages}
items=data['items']
story_brands={x['brand'] for x in items}
slugs=set(re.findall(r"brand\('([^']+)'",(SITE/'data/brands.js').read_text(encoding='utf-8')))
errors=[]
assert len(story_brands)==len(items)
assert data['version']==1 and data['updatedAt']=='2026-11-17'
rows=[]
seen={}
for x in items:
    for key in ('brand','title','paragraphs','sources','photo'):
        assert key in x,(x['brand'],key)
    assert x['title'] and x['paragraphs'] and x['sources']
    words=len(' '.join(x['paragraphs']).split())
    assert 1<=len(x['paragraphs'])<=2 and words<=120,(x['brand'],words)
    if x.get('slug'): assert x['slug'] in slugs,(x['brand'],x['slug'])
    for s in x['sources']:
        assert s['title'] and urlparse(s['url']).scheme in ('http','https')
    row={'brand':x['brand'],'words':words,'inArchive':x['brand'] in archive_brands,'sourceCount':len(x['sources']),'photo':bool(x['photo'])}
    p=x['photo']
    if p:
        for key in ('src','thumb','width','height','alt','caption','source','imageSource','credit','license'):
            assert p.get(key),(x['brand'],key)
        assert p['src'] not in seen,(x['brand'],seen.get(p['src']))
        seen[p['src']]=x['brand']
        for key in ('src','thumb'):
            path=(SITE/p[key]).resolve()
            assert path.is_relative_to(SITE.resolve()) and path.is_file(),path
            with Image.open(path) as im:
                im.load()
                if key=='src':
                    assert im.size==(p['width'],p['height']),(x['brand'],im.size,p['width'],p['height'])
                if p[key].startswith('assets/brand-stories/'):
                    assert im.format=='WEBP'
                    assert max(im.size)<=(1200 if key=='src' else 480),(x['brand'],key,im.size)
        row.update(src=p['src'],width=p['width'],height=p['height'],sha256=hashlib.sha256((SITE/p['src']).read_bytes()).hexdigest())
    rows.append(row)
assert not (archive_brands-story_brands),archive_brands-story_brands
result={'checkedAt':'2026-11-17','histories':len(items),'photos':len(seen),'photoExceptions':[x['brand'] for x in items if not x['photo']],'archivePackages':len(packages),'archiveBrands':len(archive_brands),'missingArchiveBrands':sorted(archive_brands-story_brands),'awaitingArchiveImport':sorted(story_brands-archive_brands),'rows':rows,'errors':errors}
(QA/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False))
