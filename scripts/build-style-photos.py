"""Merge sourced outfit photographs and rebuild their gallery entry points."""
import html
import json
import re
from pathlib import Path

SITE=Path(__file__).resolve().parents[1]/'tights-guide'
H=lambda value:html.escape(str(value),quote=True)

def main():
    registry=json.loads((SITE/'data/style-photos.json').read_text(encoding='utf-8'))
    photos=registry['items'];ids=set();new=[]
    for p in photos:
        ident=p['id']
        if not re.fullmatch(r'style-[a-z0-9-]+',ident) or ident in ids:raise ValueError('Invalid or duplicate style ID')
        ids.add(ident)
        for key in ('src','thumb'):
            if not re.fullmatch(r'assets/style/[a-z0-9-]+\.webp',p[key]) or not (SITE/p[key]).is_file():raise ValueError('Missing style image')
        if p.get('denVerified') and (type(p.get('den')) is not int or not 1<=p['den']<=200 or not p.get('model')):raise ValueError('Missing density evidence')
        new.append(dict(id=ident,image=p['src'],thumbnail=p['thumb'],title=p['title'],category=p['category'],
            tags=p['tags'],author=p['credit'],source=p['source'],origin='publisher',
            license='Фотография из указанной публикации; права принадлежат её автору.',licenseUrl=p['source'],
            width=p['width'],height=p['height'],alt=p['alt'],caption=p['caption'],
            den=p.get('den'),denVerified=p['denVerified'],brand=p.get('brand',''),model=p.get('model',''),
            srcset=f"{p['thumb']} {p.get('thumbWidth',min(480,p['width'],int(p['width']*650/p['height'])))}w, {p['src']} {p['width']}w"))
    path=SITE/'data/editorial-media.json';old=json.loads(path.read_text(encoding='utf-8'))
    merged=new+[p for p in old if not p['id'].startswith('style-')]
    path.write_text(json.dumps(merged,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (SITE/'data/photos.js').write_text('window.PHOTO_DATA='+json.dumps([p for p in merged if p['category'] not in ('business','archive')],ensure_ascii=False)+';\n',encoding='utf-8')

    def card(p):
        label=f"{p['den']} DEN · {p['brand']}" if p.get('denVerified') else p['sourceLabel']
        return f'''<figure><a href="lookbook.html#photo-{H(p['id'])}" aria-label="Открыть: {H(p['title'])}"><img src="{H(p['src'])}" srcset="{H(p['thumb'])} {p['thumbWidth']}w, {H(p['src'])} {p['width']}w" sizes="(max-width: 620px) 90vw, 32vw" alt="{H(p['alt'])}" width="{p['width']}" height="{p['height']}" loading="lazy"></a><figcaption><strong>{H(p['title'])}</strong><span>{H(label)}</span></figcaption></figure>'''
    byid={p['id']:p for p in photos}
    outfit_ids=['style-better-shorts','style-better-sneakers','style-better-tailoring','style-nylo-white-shirt']
    couple_ids=[p['id'] for p in photos if p['category']=='couple']
    section='''<!-- tonko-style-photos --><section class="portal-container style-collection" id="men-photo-collection"><p class="portal-eyebrow">Гардероб без шаблонов</p><h2>Прозрачность.<br>Свой способ носить.</h2><p class="style-intro">Шорты, пиджак, привычная обувь — колготки становятся частью комплекта. Смотрите фотографии целиком и сохраняйте понравившиеся сочетания.</p><div class="style-photo-grid">'''+''.join(card(byid[i]) for i in outfit_ids)+'''</div><a class="experience-text-link" href="lookbook.html?filter=men">Все мужские фотографии →</a><div class="style-density"><div><p class="portal-eyebrow">Плотность указана брендом</p><h3>10, 20 и 40 DEN</h3><p>Отдельная подборка каталожных снимков NYLO и Glamory. Для уличных кадров без маркировки плотность не определяем на глаз.</p><a class="experience-text-link" href="lookbook.html?filter=men-sheer">Рассмотреть модели до 40 DEN →</a></div><div class="style-density-images">'''+''.join(card(byid[i]) for i in ['style-nylo10-black','style-glamory-classic20-black','style-glamory-support40-black'])+'''</div></div><h3>Вдвоём</h3><p class="style-intro">Городская прогулка и архивная съёмка бренда. Близкие оттенки или общий рисунок связывают два образа.</p><div class="style-photo-grid style-couple-grid">'''+''.join(card(byid[i]) for i in couple_ids)+'''</div><a class="experience-text-link" href="lookbook.html?filter=couple">Парные образы в галерее →</a></section><!-- /tonko-style-photos -->'''
    path=SITE/'men.html';text=path.read_text(encoding='utf-8')
    text=re.sub(r'<!-- tonko-style-photos -->.*?<!-- /tonko-style-photos -->','',text,flags=re.S)
    anchor='<!-- experience-related -->'
    if anchor not in text:anchor='</main>'
    text=text.replace(anchor,section+anchor,1)
    if 'href="style-photos.css' not in text:text=text.replace('</head>','<link rel="stylesheet" href="style-photos.css?v=14"></head>')
    path.write_text(text,encoding='utf-8')
    path=SITE/'lookbook.html';text=path.read_text(encoding='utf-8')
    for value,label in [('men-sheer','Мужские ≤40 DEN'),('couple','Вдвоём')]:
        if f'data-gallery-filter="{value}"' not in text:
            text=re.sub(r'(<button[^>]*data-gallery-filter="men"[^>]*>.*?</button>)',lambda m:m[1]+f'<button data-gallery-filter="{value}" aria-pressed="false">{label}</button>',text,count=1)
    path.write_text(text,encoding='utf-8')
    for path in SITE.glob('*.html'):
        text=path.read_text(encoding='utf-8');text=re.sub(r'editorial\.js(?:\?v=[^"\s]+)?','editorial.js?v=20261116-14',text)
        path.write_text(text,encoding='utf-8')
    print(f'Style gallery: {len(photos)} new photographs; total {len(merged)} media records')

if __name__=='__main__':main()
