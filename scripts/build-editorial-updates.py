"""Extend TONKO editorials with topic-matched complete Russian editions."""
from pathlib import Path
from hashlib import sha256
from html import escape as H
from datetime import datetime, timezone
import json
import re
from news_publication import is_ready

SITE=Path(__file__).resolve().parents[1]/'tights-guide'
BASE_ADDITION='2026-11-26'
TOPICS={
 'light':(r'блеск|матов|блик|свет|глян|shine|shiny|matte', 'Проверьте впечатление от фотографии',
          ['Сравните светлые и тёмные участки одной ноги: где видна ткань, а где — отражение света?', 'Посмотрите второй ракурс той же модели. Меняется ли блеск вместе с направлением освещения?', 'Запишите отдельно наблюдение («вижу блик») и предположение («изделие всегда блестящее»). Фото подтверждает только первое.']),
 'patterns':(r'рисун|узор|кружев|горош|клетк|ромб|геометр|pattern|lace|argyle', 'Соберите сочетание вокруг одного рисунка',
          ['Выберите крупный или мелкий мотив и посмотрите на него с расстояния: какую часть образа он делает главной?', 'Сопоставьте рисунок с краем юбки, шортов и высотой обуви. Важно, какая часть узора останется видимой.', 'Найдите в одежде один цвет, который поддерживает рисунок. Затем сравните результат с полностью нейтральным верхом.']),
 'construction':(r'пояс|посадк|шов|мысок|ластов|конструк|сполза|waist|seam|toe|fit', 'Проверка посадки в движении',
          ['Сначала расправьте ткань от стопы вверх. Не пытайтесь исправить недостаток длины одним рывком за пояс.', 'Присядьте и наклонитесь: проверьте пояс, шаговую зону и швы. Давление, провисание и постоянное сползание — разные наблюдения.', 'Сопоставьте ощущения с таблицей выбранной модели. Универсального соответствия размеров разных брендов нет.']),
 'product-card':(r'размер|состав|сравнен|выбор|выбрать|den|различ|карточк|size|compare', 'Пять строк перед покупкой',
          ['Выпишите точную модель, состав и размерную таблицу. Не переносите размер автоматически с другой марки.', 'Разделите проверяемые признаки и рекламные обещания: усиленный мысок — деталь конструкции, «не рвутся» — утверждение, требующее условий.', 'Проверьте фотографии нужного оттенка, правила ухода и условия возврата. Сохраните вопросы, на которые карточка не отвечает.']),
 'making':(r'производ|переработ|упаков|сырь|волок|фабрик|production|recycl|packag|material', 'От заявления к проверяемому факту',
          ['Разделите сведения о конкретном изделии и описание компании в целом. Общий рассказ о производстве не подтверждает состав каждой пары.', 'Уточните, к чему относится экологическое заявление: сырью, упаковке, энергии или программе сбора.', 'Посмотрите, кто сообщает данные и за какой период. Слова бренда и независимая проверка имеют разный статус.']),
 'archive':(r'истори|архив|основател|основан|поколен|хронолог|history|founded|heritage', 'Соберите маленькую хронологию',
          ['Выберите один бренд и отдельно выпишите основание компании, запуск марки и появление интересующей модели.', 'Сверьте имена и даты по официальной хронологии и подписи к архивному документу.', 'Если источники расходятся, сохраните обе версии с атрибуцией. Не соединяйте их в одну уверенную дату без дополнительного подтверждения.'])
}


def select(topic,items,limit=3):
    pattern=re.compile(r'\b(?:'+TOPICS[topic][0]+')',re.I);result=[];seen=set()
    for item in items:
        if not is_ready(item) or not item.get('illustration',{}).get('src','').startswith('assets/'):continue
        if not re.search('[а-яё]',item.get('displayTitle',''),re.I):continue
        title=item['displayTitle'];intro=item.get('summary','')
        score=3*len(pattern.findall(title))+len(pattern.findall(intro))
        if score<2:continue
        key=item.get('publisherUrl') or item.get('url')
        if key in seen:continue
        seen.add(key);result.append(item)
    return sorted(result,key=lambda p:p.get('publishedAt') or '',reverse=True)[:limit]


def addition_date(items):
    dates=[BASE_ADDITION]
    for item in items:
        meta=item.get('localSummary') or item.get('ai') or {}
        stamp=meta.get('editorialReviewAt') or meta.get('generatedAt') or item.get('publishedAt')
        if stamp:
            try:
                parsed=datetime.fromisoformat(stamp.replace('Z','+00:00'))
                parsed=parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
                if parsed<=datetime.now(timezone.utc):dates.append(parsed.date().isoformat())
            except ValueError:pass
    return max(dates)


def build():
    news=json.loads((SITE/'data/news.json').read_text(encoding='utf-8'))
    journal_path=SITE/'data/journal.js';raw=journal_path.read_text(encoding='utf-8');journal=json.loads(raw[raw.index('['):].rstrip(';\n'))
    updates={};journal_html=(SITE/'journal.html').read_text(encoding='utf-8')
    journal_html=re.sub(r'<!-- editorial-update-status -->.*?<!-- /editorial-update-status -->','',journal_html,flags=re.S)
    for story in journal:
        topic=story['id'];items=select(topic,news['items']);day=addition_date(items)
        practice_title,practice=TOPICS[topic][1:]
        cards=''
        for item in items:
            photo=item['illustration'];intro=item['summary']
            cards+=f'''<article class="editorial-update-card"><img src="{H(photo['src'])}" alt="{H(photo.get('alt',''))}" loading="lazy" width="{photo.get('width',960)}" height="{photo.get('height',640)}"><div><p class="portal-eyebrow">{H(item['source'])}</p><h3><a href="news.html#story-{H(item['id'])}" data-editorial-news="{H(item['id'])}">{H(item['displayTitle'])}</a></h3><p>{H(intro)}</p><a href="news.html#story-{H(item['id'])}" data-editorial-news="{H(item['id'])}">Прочитать обзор на ТОНКО →</a><p class="editorial-update-credit">{H(photo.get('caption',''))}</p></div></article>'''
        heading=f'<p class="editorial-update-date">Последнее дополнение: <time datetime="{day}">{datetime.fromisoformat(day).strftime("%d.%m.%Y")}</time></p>'
        block=f'''<!-- editorial-updates --><section class="portal-container editorial-updates" id="editorial-updates"><p class="portal-eyebrow">Продолжение разбора</p><h2>От идеи — к реальным примерам.</h2>{heading}<div class="editorial-practice"><h3>{H(practice_title)}</h3><ol>{''.join('<li>'+H(p)+'</li>' for p in practice)}</ol><a href="guide.html">Попробовать в мастерской выбора →</a></div>'''
        if items:block+='<h3 class="editorial-new-heading">Что добавилось по теме</h3><p class="editorial-update-intro">Подборка пополняется готовыми русскими обзорами. Оригинальные даты и источники сохранены внутри материалов.</p><div class="editorial-update-list">'+cards+'</div>'
        else:block+='<p class="editorial-update-intro">Здесь будут появляться новые примеры после подготовки подходящего обзора. Пока можно пройти практику выше и свериться с источниками статьи.</p>'
        block+='</section><!-- /editorial-updates -->'
        path=SITE/story['url'];text=path.read_text(encoding='utf-8')
        text=re.sub(r'<!-- editorial-updates -->.*?<!-- /editorial-updates -->','',text,flags=re.S)
        text=re.sub(r'<!-- editorial-updates:assets -->.*?<!-- /editorial-updates:assets -->','',text,flags=re.S)
        point=text.index('</article>',text.index('<article data-reader='));text=text[:point]+block+text[point:]
        css=sha256((SITE/'editorial-updates.css').read_bytes()).hexdigest()[:12]
        text=text.replace('</head>',f'<!-- editorial-updates:assets --><link rel="stylesheet" href="editorial-updates.css?v={css}"><link rel="stylesheet" href="news-reader.css?v=20261117-17"><!-- /editorial-updates:assets --></head>')
        js=sha256((SITE/'editorial-updates.js').read_bytes()).hexdigest()[:12];reader=sha256((SITE/'news-reader.js').read_bytes()).hexdigest()[:12]
        seed=json.dumps(items,ensure_ascii=False).replace('<','\\u003c')
        text=text.replace('</body>',f'<!-- editorial-updates:assets --><script type="application/json" id="editorial-updates-data">{seed}</script><script src="news-reader.js?v={reader}" defer></script><script src="editorial-updates.js?v={js}" defer></script><!-- /editorial-updates:assets --></body>')
        path.write_text(text,encoding='utf-8')
        status=f'<!-- editorial-update-status --><p class="editorial-update-date">Дополнено {datetime.fromisoformat(day).strftime("%d.%m.%Y")} · '+(f'{len(items)} примера по теме' if items else 'редакционная практика')+'</p><!-- /editorial-update-status -->'
        pattern=r'(<article class="journal-row"[^>]*data-story="'+re.escape(topic)+r'".*?)(<div class="journal-row-actions">)'
        journal_html=re.sub(pattern,lambda m:m[1]+status+m[2],journal_html,count=1,flags=re.S)
        story['updatedAt']=day;story['updateCount']=len(items)
        updates[topic]={'updatedAt':day,'ids':[p['id'] for p in items]}
    journal_path.write_text('window.TONKO_JOURNAL = '+json.dumps(journal,ensure_ascii=False,indent=2)+';\n',encoding='utf-8')
    journal_html=re.sub(r'(<p>Авторские разборы ТОНКО) · <time[^>]*>.*?</time>(</p>)',r'\1 · дополняются новыми примерами\2',journal_html)
    journal_html=re.sub(r'<!-- editorial-updates:assets -->.*?<!-- /editorial-updates:assets -->','',journal_html,flags=re.S)
    journal_html=journal_html.replace('</head>',f'<!-- editorial-updates:assets --><link rel="stylesheet" href="editorial-updates.css?v={css}"><!-- /editorial-updates:assets --></head>')
    (SITE/'journal.html').write_text(journal_html,encoding='utf-8')
    (SITE/'data/editorial-updates.json').write_text(json.dumps(updates,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Extended author editorials:',{k:len(v['ids']) for k,v in updates.items()})


if __name__=='__main__':build()
