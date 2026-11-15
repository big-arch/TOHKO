"""Run after both HTML builders. Pillow creates display derivatives; originals stay intact."""
from pathlib import Path
from html.parser import HTMLParser
import json,re,html
from PIL import Image,ImageOps
R=Path(__file__).resolve().parents[1];S=R/'tights-guide';out=S/'assets/responsive';out.mkdir(exist_ok=True)
media=json.loads((S/'data/editorial-media.json').read_text(encoding='utf-8'))
for m in media:
 with Image.open(S/m['image']) as source:
  im=ImageOps.exif_transpose(source).convert('RGB')
  widths=sorted(set([w for w in (320,640,960,1440) if w<im.width]+[min(im.width,1440)]))
  variants=[]
  for w in widths:
   dest=out/f'{m["id"]}-{w}.webp'
   if not dest.exists() or dest.stat().st_mtime<(S/m['image']).stat().st_mtime:
    resized=im.resize((w,round(im.height*w/im.width)),Image.Resampling.LANCZOS)
    resized.save(dest,'WEBP',quality=88,method=6)
   variants.append({'src':dest.relative_to(S).as_posix(),'width':w,'bytes':dest.stat().st_size})
  m['responsive']=variants
  m['srcset']=', '.join(f'{v["src"]} {v["width"]}w' for v in variants)
by_path={m['image']:m for m in media}
class Tag(HTMLParser):
 def handle_starttag(self,tag,attrs):self.attrs=dict(attrs)
def enhance(match):
 tag=match[0];parser=Tag();parser.feed(tag);a=parser.attrs;m=by_path.get(a.get('src'))
 if not m or a.get('id') in ('detail-image','editorial-full-image'):return tag
 for attr in ('srcset','sizes','decoding','fetchpriority'):
  tag=re.sub(r'\s'+attr+r'="[^"]*"','',tag)
 lazy=a.get('loading')=='lazy'
 sizes=('auto, ' if lazy else '')+'(max-width: 540px) 100vw, 50vw'
 attrs=f' srcset="{m["srcset"]}" sizes="{sizes}" decoding="async"'
 if a.get('loading')=='eager':attrs+=' fetchpriority="high"'
 return tag[:-1]+attrs+'>'
for p in S.glob('*.html'):
 p.write_text(re.sub(r'<img\b[^>]*>',enhance,p.read_text(encoding='utf-8')),encoding='utf-8')
(S/'data/editorial-media.json').write_text(json.dumps(media,ensure_ascii=False,indent=2),encoding='utf-8')
(S/'data/photos.js').write_text('window.PHOTO_DATA = '+json.dumps([m for m in media if m['category'] not in ('business','archive')],ensure_ascii=False,indent=2)+';\n',encoding='utf-8')
print('Responsive variants:',sum(len(m['responsive']) for m in media),'for',len(media),'originals')
