(() => {
  'use strict';
  const escape = s => String(s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const data=window.BRAND_DATA || [];
  const sourceList=item=>`<ul class="tonko-source-list">${(item.historySources||[]).map(s=>`<li><a href="${escape(s.url)}" target="_blank" rel="noopener">${escape(s.title)} ↗</a><small>${escape(s.supports)}</small></li>`).join('')}</ul>`;

  // Shared links do not depend on a build step or an absolute deployment path.
  document.querySelectorAll('.portal-nav').forEach(nav=>{
    if(!nav.querySelector('a[href="search.html"]')) {
      const a=document.createElement('a');a.href='search.html';a.textContent='Поиск';nav.append(a);
    }
  });
  document.querySelectorAll('.portal-footer-bottom,.site-footer .footer-bottom').forEach(footer=>{
    const a=document.createElement('a');a.href='sources.html';a.textContent='Источники и фото';footer.append(a);
  });

  const item=data.find(b=>b.slug===new URLSearchParams(location.search).get('brand'));
  const prose=document.querySelector('#brand-bio');
  if(item&&prose) {
    const section=document.createElement('section');section.id='history-sources';
    section.innerHTML=`<h2>Источники истории</h2><p class="tonko-note">${item.historyReviewed?`Сверено ${item.historyChecked}. ${escape(item.historyNote)}`:'Отдельная историческая проверка ещё не завершена. Ниже сохранено описание из исходного каталога; подтверждённая дата основания не добавляется.'}</p>${sourceList(item)}<p class="tonko-note">Актуальность моделей проверяется отдельно по ссылкам в таблице. <a href="sources.html">Реестр проверки</a>.</p>`;
    prose.parentElement.append(section);
    if(!item.historyReviewed) {
      const notice=document.createElement('p');notice.className='tonko-note';notice.textContent='Каталожная справка. Исторические сведения требуют отдельного подтверждения.';prose.before(notice);
    }
  }
  const register=document.querySelector('#history-register');
  if(register) register.innerHTML=data.map(b=>`<article><h2><a href="brand.html?brand=${escape(b.slug)}">${escape(b.name)} ↗</a></h2><p>${b.historyReviewed?`Сверено ${b.historyChecked}. ${escape(b.historyNote)}`:'Историческая хронология пока не подтверждена. Каталожная справка сохранена без добавления предполагаемых дат.'}</p>${sourceList(b)}</article>`).join('');

  const photoRegister=document.querySelector('#photo-register');
  if(photoRegister) photoRegister.innerHTML=(window.PHOTO_DATA||[]).map(p=>`<li><a href="${escape(p.source)}" target="_blank" rel="noopener">${escape(p.title)}</a><small>${escape(p.author)} · <a href="${escape(p.licenseUrl)}">${escape(p.license)}</a>. Уменьшение размера и кадрирование при отображении.</small></li>`).join('');

  fetch('data/logo-sources.json').then(r=>{if(!r.ok)throw new Error('Logo manifest unavailable');return r.json();}).then(logos=>{
    const insertLogo=(host,slug)=>{
      const logo=logos[slug];
      if(!logo||host.querySelector('.tonko-brand-logo'))return;
      const name=data.find(b=>b.slug===slug)?.name||slug;
      const a=document.createElement('a');a.href=logo.source;a.target='_blank';a.rel='noopener';a.className='tonko-brand-logo'+(logo.dark?' on-dark':'');a.title=`Оригинальный логотип ${name}: источник`;
      const img=document.createElement('img');img.src=logo.path;img.alt=`Логотип ${name}`;img.loading='lazy';img.addEventListener('error',()=>a.remove(),{once:true});a.append(img);host.prepend(a);
    };
    const decorate=()=>{
      document.querySelectorAll('.portal-brand-tile,.portal-catalog-card').forEach(card=>{
        const link=card.querySelector('a[href*="brand.html?brand="]');if(!link)return;
        insertLogo(card,new URL(link.href).searchParams.get('brand'));
      });
    };
    decorate();
    const catalog=document.querySelector('#brand-catalog-grid');
    if(catalog) new MutationObserver(decorate).observe(catalog,{childList:true});
    if(item&&prose) insertLogo(document.querySelector('#brand-title').parentElement,item.slug);
    const list=document.querySelector('#logo-register');
    if(list)list.innerHTML=Object.entries(logos).map(([slug,l])=>`<li><a href="${escape(l.source)}" target="_blank" rel="noopener">${escape(data.find(b=>b.slug===slug)?.name||slug)}</a><small>Оригинальный файл с сайта бренда. <a href="${escape(l.asset)}" target="_blank" rel="noopener">Файл-источник</a>. Получен 15 ноября 2026.</small></li>`).join('');
  }).catch(()=>{/* Brand names remain usable when the manifest is unavailable. */});
})();
