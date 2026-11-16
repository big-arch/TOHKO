(() => {
  'use strict';
  const collator=new Intl.Collator('ru',{sensitivity:'base',numeric:true});
  const rows=[...(window.TONKO_PACKAGING||[])].sort((a,b)=>collator.compare(a.brand,b.brand)||collator.compare(a.title,b.title)), $=id=>document.getElementById(id);if(!$('pack-grid'))return;
  const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const normal=v=>v.toLocaleLowerCase('ru').replaceAll('ё','е');
  const brands=[...new Set(rows.map(r=>r.brand))];
  const dialog=$('pack-dialog');let shown=rows,current=0,opener=null,oldOverflow='';
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
    $('pack-variants').replaceChildren();if(r.variants.length){const p=document.createElement('p');p.textContent='Другие изображения и карточки этой упаковки:';$('pack-variants').append(p);r.variants.forEach(v=>{const a=document.createElement('a');a.href=v.source;a.target='_blank';a.rel='noopener noreferrer';a.textContent=v.title+' ↗';$('pack-variants').append(a);if(v.image){const photo=document.createElement('a');photo.href=v.image;photo.target='_blank';photo.rel='noopener noreferrer';photo.textContent='Рассмотреть дополнительное фото ↗';$('pack-variants').append(photo);}});}
    $('pack-previous').disabled=$('pack-next').disabled=shown.length<2;
    const u=new URL(location.href);u.searchParams.set('pack',r.id);history.replaceState(null,'',u);
  }
  function open(id){const index=shown.findIndex(r=>r.id===id);if(index<0)return;current=index;opener=document.activeElement;oldOverflow=document.documentElement.style.overflow;display();dialog.showModal();document.documentElement.style.overflow='hidden';}
  $('pack-grid').addEventListener('click',e=>{const a=e.target.closest('[data-pack]');if(a&&!e.ctrlKey&&!e.metaKey){e.preventDefault();open(a.dataset.pack);}
    const more=e.target.closest('[data-more-brand]');if(more){const b=more.dataset.moreBrand,group=shown.filter(r=>r.brand===b),previous=limits.get(b)||($('pack-brand').value==='all'?4:36);limits.set(b,previous+($('pack-brand').value==='all'?12:36));render();const first=group[previous];if(first)$('pack-grid').querySelector(`[data-pack="${CSS.escape(first.id)}"]`)?.focus({preventScroll:true});}
  });
  $('pack-brand-links').addEventListener('click',e=>{const a=e.target.closest('[data-brand]');if(!a||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();$('pack-brand').value=a.dataset.brand;limits.clear();render();if(matchMedia('(max-width:800px)').matches)$('pack-directory').open=false;$('package-archive').scrollIntoView({block:'start'});$('pack-brand').focus({preventScroll:true});});
  $('pack-close').onclick=()=>dialog.close();dialog.addEventListener('close',()=>{document.documentElement.style.overflow=oldOverflow;const u=new URL(location.href);u.searchParams.delete('pack');history.replaceState(null,'',u);opener?.focus({preventScroll:true});});
  function change(n){if(shown.length){current=(current+n+shown.length)%shown.length;display();}}
  $('pack-previous').onclick=()=>change(-1);$('pack-next').onclick=()=>change(1);
  dialog.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();change(e.key==='ArrowLeft'?-1:1);}});
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
