(() => {
  'use strict';
  const collator=new Intl.Collator('ru',{sensitivity:'base',numeric:true});
  const rows=[...(window.TONKO_PACKAGING||[])].sort((a,b)=>collator.compare(a.brand,b.brand)||collator.compare(a.title,b.title)), $=id=>document.getElementById(id);if(!$('pack-grid'))return;
  const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const normal=v=>v.toLocaleLowerCase('ru').replaceAll('ё','е');
  const brands=[...new Set(rows.map(r=>r.brand))];
  const dialog=$('pack-dialog');let shown=rows,current=0,opener=null,oldOverflow='',activePhotos=[],photoIndex=0;
  const looks=window.TONKO_PACKAGE_LOOKS?.items||[];
  const exactKey=v=>normal(String(v||'')).normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-zа-я0-9]+/g,' ').trim();
  const photoDialog=$('pack-photo-dialog');
  document.querySelector('.pack-looks').after(document.querySelector('.pack-styling'));
  function keepDialogFocus(e,modal){if(e.key!=='Tab')return;const controls=[...modal.querySelectorAll('button:not([disabled]),a[href],summary,input:not([disabled]),select:not([disabled]),[tabindex]:not([tabindex="-1"])')].filter(el=>el.getClientRects().length);if(!controls.length)return;const first=controls[0],last=controls[controls.length-1];if(e.shiftKey&&(document.activeElement===first||!modal.contains(document.activeElement))){e.preventDefault();last.focus();}else if(!e.shiftKey&&(document.activeElement===last||!modal.contains(document.activeElement))){e.preventDefault();first.focus();}}
  let stylePhotos=window.TONKO_STYLE_PHOTOS?.items||[],stylesReady=null;
  function findLooks(r){return looks.find(x=>Array.isArray(x.packageIds)&&x.packageIds.includes(r.id)&&exactKey(x.exactMatch?.brand)===exactKey(r.brand)&&x.exactMatch?.den===r.den);}
  function suggestions(r){
    if(r.productKind==='легинсы')return 'Попробуйте удлинённый жакет или свободный трикотаж и лаконичную обувь. Посадку и длину сверяйте с карточкой модели.';
    if(r.productKind==='гольфы')return 'Попробуйте миди или укороченные брюки с лоферами. Проверьте, где заканчивается манжета и видна ли она в движении.';
    if(r.den===null)return 'Начните с одного акцента: рисунка, цвета или фактуры. Подберите спокойную одежду и проверьте сочетание при дневном свете.';
    if(r.den<=20)return 'Тонкие колготки можно сочетать с платьем, юбкой или строгими шортами. Для спокойного образа подберите близкий к обуви оттенок.';
    if(r.den<=50)return 'Попробуйте юбку миди, жакет или трикотажное платье. Оттенок обуви в тон колготкам помогает собрать цельное сочетание.';
    return 'Попробуйте плотный трикотаж, шерстяную юбку или свободные шорты с ботинками. Гладкая одежда уравновесит выраженную фактуру.';
  }
  function inspiration(r){
    const hints=r.den!==null&&r.den<=20?['sheer','тонкие','прозрачные']:r.den!==null&&r.den>=60?['opaque','плотные','трикотаж']:['tights','колготки','skirt','юбка'];
    return stylePhotos.filter(p=>p.src&&p.thumb).map(p=>({p,score:(p.tags||[]).filter(t=>hints.some(h=>normal(String(t)).includes(h))).length})).sort((a,b)=>b.score-a.score).slice(0,2).map(({p})=>({...p,matchType:'inspiration'}));
  }
  function renderDetails(r){
    const matched=findLooks(r),kind=r.productKind||'колготки';
    $('pack-facts').innerHTML=`<div><dt>Тип изделия</dt><dd>${esc(kind)}</dd></div><div><dt>DEN в названии</dt><dd>${r.den===null?'Не указано':esc(r.den)+' DEN'}</dd></div>`;
    $('pack-styling').textContent=suggestions(r);
    activePhotos=matched?.photos?.length?matched.photos.map(p=>({...p,matchType:'exact'})):inspiration(r);
    $('pack-looks-title').textContent=matched?'На модели: '+matched.model:'Идеи сочетаний';
    $('pack-looks-note').textContent=matched?'Каталожные фотографии этой модели. Источник подтверждает название; цвет и выпуск могут отличаться от упаковки.':activePhotos.length?'Проверенных дополнительных фото этой модели пока нет. Ниже — идеи сочетаний: бренд и модель колготок на этих снимках могут отличаться.':'Проверенных дополнительных фото этой модели пока нет. Используйте идею сочетания выше и ссылку на карточку источника.';
    $('pack-looks-grid').innerHTML=activePhotos.map((p,i)=>`<figure class="pack-look"><button type="button" class="pack-look-open" data-look-index="${i}" aria-label="Увеличить: ${esc(p.alt||p.title)}"><img src="${esc(p.thumb||p.src)}" alt="${esc(p.alt||p.title)}" width="${Number(p.width)||600}" height="${Number(p.height)||800}" loading="${i<2?'eager':'lazy'}" decoding="async"><span aria-hidden="true">↗</span></button><figcaption>${esc(p.caption||p.title)}${p.matchType==='inspiration'?'<small>Идея сочетания · другая или неустановленная модель</small>':''}</figcaption></figure>`).join('');
    $('pack-looks-grid').hidden=!activePhotos.length;
    if(!matched&&!stylePhotos.length&&!stylesReady){stylesReady=fetch('data/style-photos.json').then(res=>res.ok?res.json():null).then(data=>{stylePhotos=Array.isArray(data?.items)?data.items:[];if(dialog.open&&shown[current])renderDetails(shown[current]);}).catch(()=>{});}
  }
  function displayPhoto(index){photoIndex=(index+activePhotos.length)%activePhotos.length;const p=activePhotos[photoIndex];if(!p)return;$('pack-photo-full').src=p.src;$('pack-photo-full').alt=p.alt||p.title;$('pack-photo-title').textContent=p.title;$('pack-photo-caption').textContent=p.caption||p.alt;$('pack-photo-source').href=p.source;$('pack-photo-source').textContent=(p.sourceLabel||p.credit||'Источник фотографии')+' ↗';$('pack-photo-match').textContent=p.matchType==='exact'?'Фотография конкретной модели':'Идея сочетания · это не подтверждённое фото выбранной модели';$('pack-photo-position').textContent=`${photoIndex+1} / ${activePhotos.length}`;$('pack-photo-previous').disabled=$('pack-photo-next').disabled=activePhotos.length<2;}
  const limits=new Map();
  $('pack-directory').open=!matchMedia('(max-width:800px)').matches;
  const params=new URLSearchParams(location.search);
  $('pack-search').value=params.get('q')||'';
  if(rows.some(r=>r.brand===params.get('brand')))$('pack-brand').value=params.get('brand');
  if(['thin','medium','dense','unknown'].includes(params.get('den')))$('pack-den').value=params.get('den');
  function url(){const u=new URL(location.href);for(const [k,v] of Object.entries({q:$('pack-search').value.trim(),brand:$('pack-brand').value,den:$('pack-den').value})){if(v&&v!=='all')u.searchParams.set(k,v);else u.searchParams.delete(k);}history.replaceState(null,'',u);}
  function card(r){return `<article class="pack-card"><a class="pack-open" href="${esc(r.image)}" data-pack="${esc(r.id)}" aria-label="Рассмотреть упаковку: ${esc(r.title)}"><img src="${esc(r.thumbnail)}" alt="Упаковка ${esc(r.title)}" width="${r.width}" height="${r.height}" loading="lazy" decoding="async"></a><h3>${esc(r.title)}</h3></article>`;}
  function brandUrl(brand){const u=new URL(location.href);u.searchParams.delete('pack');if(brand==='all')u.searchParams.delete('brand');else u.searchParams.set('brand',brand);u.hash='package-archive';return u.pathname+u.search+u.hash;}
  function render(update=true){
    const q=normal($('pack-search').value.trim()),brand=$('pack-brand').value,den=$('pack-den').value;
    shown=rows.filter(r=>(brand==='all'||r.brand===brand)&&normal([r.title,r.brand,...r.variants.map(v=>v.title)].join(' ')).includes(q)&&(den==='all'||den==='unknown'&&r.den===null||den==='thin'&&r.den>0&&r.den<=20||den==='medium'&&r.den>20&&r.den<=50||den==='dense'&&r.den>=60));
    if(update)url();
    $('pack-brand-links').innerHTML=['all',...brands].map(b=>`<a href="${esc(brandUrl(b))}" data-brand="${esc(b)}"${b===brand?' aria-current="true"':''}><span>${esc(b==='all'?'Все бренды':b)}</span><span class="pack-brand-total">${b==='all'?rows.length:rows.filter(r=>r.brand===b).length}</span></a>`).join('');
    let visible=0,groupCount=0;
    $('pack-grid').innerHTML=brands.map(b=>{
      const group=shown.filter(r=>r.brand===b);if(!group.length)return '';groupCount++;
      const limit=limits.get(b)||(brand==='all'?4:36),part=group.slice(0,limit);visible+=part.length;
      const slug=group[0].brandSlug;
      const kindNote=group.some(r=>r.productKind&&r.productKind!=='колготки')?`<p class="pack-kind-note">Типы изделий: ${['колготки','гольфы','легинсы'].map(kind=>[kind,group.filter(r=>(r.productKind||'колготки')===kind).length]).filter(([,count])=>count).map(([kind,count])=>`${kind} — ${count}`).join(', ')}.</p>`:'';
      return `<section class="pack-brand-section" data-brand-section="${esc(b)}" aria-labelledby="brand-${esc(slug)}"><header class="pack-brand-heading"><h2 id="brand-${esc(slug)}">${esc(b)}</h2><p>Показано ${part.length} из ${group.length}</p></header>${kindNote}<div class="pack-grid">${part.map(card).join('')}</div>${part.length<group.length?`<button class="pack-more" type="button" data-more-brand="${esc(b)}">Показать ещё ${Math.min(brand==='all'?12:36,group.length-part.length)} <span class="pack-more-brand">· ${esc(b)}</span></button>`:''}</section>`;
    }).join('');
    $('pack-count').textContent=shown.length?`Найдено ${shown.length} · брендов: ${groupCount} · показано ${visible}`:'Ничего не найдено. Попробуйте другой бренд или название.';
  }
  function display(){
    const r=shown[current];if(!r)return;const img=$('pack-full');img.src=r.image;img.alt='Упаковка '+r.title;img.width=r.width;img.height=r.height;
    $('pack-image-area').classList.remove('is-zoomed');$('pack-zoom').setAttribute('aria-pressed','false');$('pack-zoom').textContent='Увеличить';
    $('pack-label').textContent=r.brand;$('pack-title').textContent=r.title;$('pack-caption').textContent=r.caption;
    $('pack-source').href=r.source;$('pack-source').textContent=r.sourceName+' ↗';$('pack-position').textContent=`${current+1} / ${shown.length}`;
    renderDetails(r);
    $('pack-variants').replaceChildren();if(r.variants.length){const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Другие изображения и источники упаковки ('+r.variants.length+')';details.append(summary);$('pack-variants').append(details);r.variants.forEach(v=>{const a=document.createElement('a');a.href=v.source;a.target='_blank';a.rel='noopener noreferrer';a.textContent=v.title+' ↗';details.append(a);if(v.image){const photo=document.createElement('a');photo.href=v.image;photo.target='_blank';photo.rel='noopener noreferrer';photo.textContent='Рассмотреть дополнительное фото ↗';details.append(photo);}});}
    $('pack-previous').disabled=$('pack-next').disabled=shown.length<2;
    const u=new URL(location.href);u.searchParams.set('pack',r.id);history.replaceState(null,'',u);
  }
  function open(id){const index=shown.findIndex(r=>r.id===id);if(index<0)return;current=index;opener=document.activeElement;oldOverflow=document.documentElement.style.overflow;display();dialog.showModal();document.documentElement.style.overflow='hidden';}
  $('pack-grid').addEventListener('click',e=>{const a=e.target.closest('[data-pack]');if(a&&!e.ctrlKey&&!e.metaKey){e.preventDefault();open(a.dataset.pack);}
    const more=e.target.closest('[data-more-brand]');if(more){const b=more.dataset.moreBrand,group=shown.filter(r=>r.brand===b),previous=limits.get(b)||($('pack-brand').value==='all'?4:36);limits.set(b,previous+($('pack-brand').value==='all'?12:36));render();const first=group[previous];if(first)$('pack-grid').querySelector(`[data-pack="${CSS.escape(first.id)}"]`)?.focus({preventScroll:true});}
  });
  $('pack-brand-links').addEventListener('click',e=>{const a=e.target.closest('[data-brand]');if(!a||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();$('pack-brand').value=a.dataset.brand;limits.clear();render();if(matchMedia('(max-width:800px)').matches)$('pack-directory').open=false;$('package-archive').scrollIntoView({block:'start'});$('pack-brand').focus({preventScroll:true});});
  $('pack-close').onclick=()=>dialog.close();dialog.addEventListener('close',()=>{document.documentElement.style.overflow=oldOverflow;const u=new URL(location.href);u.searchParams.delete('pack');history.replaceState(null,'',u);opener?.focus({preventScroll:true});});
  function change(n){if(shown.length){current=(current+n+shown.length)%shown.length;display();if(dialog.open&&!dialog.contains(document.activeElement))$(n<0?'pack-previous':'pack-next').focus();}}
  $('pack-previous').onclick=()=>change(-1);$('pack-next').onclick=()=>change(1);
  $('pack-looks-grid').addEventListener('click',e=>{const button=e.target.closest('[data-look-index]');if(!button)return;displayPhoto(Number(button.dataset.lookIndex));photoDialog.showModal();});
  $('pack-photo-close').onclick=()=>photoDialog.close();
  $('pack-photo-previous').onclick=()=>displayPhoto(photoIndex-1);$('pack-photo-next').onclick=()=>displayPhoto(photoIndex+1);
  photoDialog.addEventListener('keydown',e=>{keepDialogFocus(e,photoDialog);if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();e.stopPropagation();displayPhoto(photoIndex+(e.key==='ArrowLeft'?-1:1));}});
  photoDialog.addEventListener('click',e=>{if(e.target===photoDialog){const r=photoDialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)photoDialog.close();}});
  dialog.addEventListener('keydown',e=>{keepDialogFocus(e,dialog);if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();change(e.key==='ArrowLeft'?-1:1);}});
  $('pack-zoom').onclick=()=>{const area=$('pack-image-area');if(!area.classList.contains('is-zoomed'))area.style.setProperty('--pack-zoom-width',Math.round($('pack-full').getBoundingClientRect().width*2)+'px');const active=area.classList.toggle('is-zoomed');$('pack-zoom').setAttribute('aria-pressed',String(active));$('pack-zoom').textContent=active?'Вписать':'Увеличить';};
  dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
  document.querySelector('.pack-tools').hidden=false;document.querySelector('.pack-tools').onsubmit=e=>e.preventDefault();
  $('pack-search').oninput=()=>{limits.clear();render();};$('pack-brand').onchange=$('pack-den').onchange=()=>{limits.clear();render();};
  $('pack-reset').onclick=()=>{$('pack-search').value='';$('pack-brand').value=$('pack-den').value='all';limits.clear();render();$('pack-search').focus();};
  const linked=rows.find(r=>r.id===params.get('pack')||r.variants.some(v=>v.id===params.get('pack')));
  if(linked){$('pack-search').value='';$('pack-den').value='all';$('pack-brand').value=linked.brand;}
  render(Boolean(linked));
  if(linked)open(linked.id);
})();
