(() => {
  'use strict';
  const rows=window.TONKO_PACKAGING||[], $=id=>document.getElementById(id);if(!$('pack-grid'))return;
  const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const normal=v=>v.toLocaleLowerCase('ru').replaceAll('ё','е');
  const dialog=$('pack-dialog');let shown=rows,limit=36,current=0,opener=null,oldOverflow='';
  const params=new URLSearchParams(location.search);
  $('pack-search').value=params.get('q')||'';
  if(rows.some(r=>r.brand===params.get('brand')))$('pack-brand').value=params.get('brand');
  if(['thin','medium','dense','unknown'].includes(params.get('den')))$('pack-den').value=params.get('den');
  function url(){const u=new URL(location.href);for(const [k,v] of Object.entries({q:$('pack-search').value.trim(),brand:$('pack-brand').value,den:$('pack-den').value})){if(v&&v!=='all')u.searchParams.set(k,v);else u.searchParams.delete(k);}history.replaceState(null,'',u);}
  function render(update=true){
    const q=normal($('pack-search').value.trim()),brand=$('pack-brand').value,den=$('pack-den').value;
    shown=rows.filter(r=>(brand==='all'||r.brand===brand)&&normal([r.title,r.brand,...r.variants.map(v=>v.title)].join(' ')).includes(q)&&(den==='all'||den==='unknown'&&r.den===null||den==='thin'&&r.den>0&&r.den<=20||den==='medium'&&r.den>20&&r.den<=50||den==='dense'&&r.den>=60));
    $('pack-grid').innerHTML=shown.slice(0,limit).map(r=>`<article class="pack-card"><a class="pack-open" href="${esc(r.image)}" data-pack="${esc(r.id)}" aria-label="Рассмотреть упаковку: ${esc(r.title)}"><img src="${esc(r.thumbnail)}" alt="Упаковка ${esc(r.title)}" width="${r.width}" height="${r.height}" loading="lazy" decoding="async"></a><p>${esc(r.brand)}</p><h2>${esc(r.title)}</h2></article>`).join('');
    $('pack-count').textContent=shown.length?`Найдено ${shown.length} · показано ${Math.min(limit,shown.length)}`:'Ничего не найдено. Попробуйте другой бренд или название.';
    $('pack-more').hidden=shown.length<=limit;$('pack-more').textContent=`Показать ещё ${Math.min(36,Math.max(0,shown.length-limit))}`;
    if(update)url();
  }
  function display(){
    const r=shown[current];if(!r)return;const img=$('pack-full');img.src=r.image;img.alt='Упаковка '+r.title;img.width=r.width;img.height=r.height;
    $('pack-image-area').classList.remove('is-zoomed');$('pack-zoom').setAttribute('aria-pressed','false');$('pack-zoom').textContent='Увеличить';
    $('pack-label').textContent=r.brand;$('pack-title').textContent=r.title;$('pack-caption').textContent=r.caption;
    $('pack-source').href=r.source;$('pack-source').textContent=r.sourceName+' ↗';$('pack-position').textContent=`${current+1} / ${shown.length}`;
    $('pack-variants').replaceChildren();if(r.variants.length){const p=document.createElement('p');p.textContent='Этот же вид упаковки в каталоге:';$('pack-variants').append(p);r.variants.forEach(v=>{const a=document.createElement('a');a.href=v.source;a.target='_blank';a.rel='noopener noreferrer';a.textContent=v.title+' ↗';$('pack-variants').append(a);});}
    $('pack-previous').disabled=$('pack-next').disabled=shown.length<2;
    const u=new URL(location.href);u.searchParams.set('pack',r.id);history.replaceState(null,'',u);
  }
  function open(id){const index=shown.findIndex(r=>r.id===id);if(index<0)return;current=index;opener=document.activeElement;oldOverflow=document.documentElement.style.overflow;display();dialog.showModal();document.documentElement.style.overflow='hidden';}
  $('pack-grid').addEventListener('click',e=>{const a=e.target.closest('[data-pack]');if(a&&!e.ctrlKey&&!e.metaKey){e.preventDefault();open(a.dataset.pack);}});
  $('pack-close').onclick=()=>dialog.close();dialog.addEventListener('close',()=>{document.documentElement.style.overflow=oldOverflow;const u=new URL(location.href);u.searchParams.delete('pack');history.replaceState(null,'',u);opener?.focus({preventScroll:true});});
  function change(n){if(shown.length){current=(current+n+shown.length)%shown.length;display();}}
  $('pack-previous').onclick=()=>change(-1);$('pack-next').onclick=()=>change(1);
  dialog.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();change(e.key==='ArrowLeft'?-1:1);}});
  $('pack-zoom').onclick=()=>{const area=$('pack-image-area');if(!area.classList.contains('is-zoomed'))area.style.setProperty('--pack-zoom-width',Math.round($('pack-full').getBoundingClientRect().width*2)+'px');const active=area.classList.toggle('is-zoomed');$('pack-zoom').setAttribute('aria-pressed',String(active));$('pack-zoom').textContent=active?'Вписать':'Увеличить';};
  dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
  document.querySelector('.pack-tools').hidden=false;document.querySelector('.pack-tools').onsubmit=e=>e.preventDefault();
  $('pack-search').oninput=()=>{limit=36;render();};$('pack-brand').onchange=$('pack-den').onchange=()=>{limit=36;render();};
  $('pack-reset').onclick=()=>{$('pack-search').value='';$('pack-brand').value=$('pack-den').value='all';limit=36;render();$('pack-search').focus();};
  $('pack-more').onclick=()=>{limit+=36;render();};render(false);
  if(params.get('pack'))open(params.get('pack'));
})();
