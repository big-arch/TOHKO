(() => {
  'use strict';
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const stories = window.TONKO_JOURNAL || [], ids = new Set(stories.map(s => s.id));
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const escape = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const press = (buttons, selected) => buttons.forEach(b => b.setAttribute('aria-pressed',String(b===selected)));
  const read = (key, fallback) => {try{return JSON.parse(localStorage.getItem(key)) ?? fallback;}catch{return fallback;}};
  let noticeTimer;
  function notify(message){
    let node=$('.experience-storage-notice');if(!node){node=document.createElement('div');node.className='experience-storage-notice';node.setAttribute('role','status');document.body.append(node);}
    node.textContent=message;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>node.remove(),6000);
  }
  function write(key, value, visible=false){try{localStorage.setItem(key,JSON.stringify(value));return true;}catch{if(visible)notify('Браузер запретил сохранение. Вы можете продолжать читать и смотреть фотографии.');return false;}}
  const savedRaw=read('tonko-reading-shelf-v1',[]);
  let saved = new Set(Array.isArray(savedRaw)?savedRaw.filter(id=>ids.has(id)):[]);
  function refreshSaveButtons(){
    $$('[data-save-story]').forEach(b=>{const on=saved.has(b.dataset.saveStory);b.setAttribute('aria-pressed',String(on));b.textContent=on?'Сохранено ✓':'Сохранить';});
  }
  $$('[data-save-story]').forEach(b=>b.addEventListener('click',()=>{
    const id=b.dataset.saveStory;if(!ids.has(id))return;
    const next=new Set(saved);next.has(id)?next.delete(id):next.add(id);
    if(write('tonko-reading-shelf-v1',[...next],true)){saved=next;refreshSaveButtons();filterJournal();}
  }));refreshSaveButtons();
  const filterButtons=$$('[data-journal-filter]');
  let journalFilter='all';
  function filterJournal(){
    if(!$('#journal-list'))return;
    let count=0;$$('#journal-list [data-story]').forEach(row=>{const show=journalFilter==='all'||(journalFilter==='saved'?saved.has(row.dataset.story):row.dataset.theme===journalFilter);row.hidden=!show;if(show)count++;});
    $('#journal-count').textContent=`Материалов: ${count}`;$('#journal-empty').hidden=count>0;
  }
  if(filterButtons.length){
    const desired=new URLSearchParams(location.search).get('topic');const selected=filterButtons.find(b=>b.dataset.journalFilter===desired)||filterButtons[0];journalFilter=selected.dataset.journalFilter;press(filterButtons,selected);
    filterButtons.forEach(b=>b.addEventListener('click',()=>{journalFilter=b.dataset.journalFilter;press(filterButtons,b);filterJournal();const url=new URL(location.href);journalFilter==='all'?url.searchParams.delete('topic'):url.searchParams.set('topic',journalFilter);history.replaceState(null,'',url);}));filterJournal();
  }
  const routes={eye:[['read-light.html','Свет и блеск'],['read-patterns.html','Рисунок и масштаб'],['textures.html','Рассмотреть под лупой']],choice:[['read-product-card.html','Прочитать карточку'],['read-construction.html','Разобрать конструкцию'],['guide.html','Собрать критерии выбора']],story:[['read-archive.html','Проверить историю'],['history.html#brand-archive','Пройти по хронологии'],['read-making.html','Увидеть производство']]};
  const routeButtons=$$('[data-route]');routeButtons.forEach(b=>b.addEventListener('click',()=>{const route=routes[b.dataset.route];if(!route)return;press(routeButtons,b);$('#route-result').innerHTML='<ol>'+route.map(([href,label])=>`<li><a href="${href}">${label}</a></li>`).join('')+'</ol>';}));
  const rawProgress=read('tonko-reading-progress-v1',{});
  const progress=rawProgress&&typeof rawProgress==='object'&&!Array.isArray(rawProgress)?rawProgress:{};
  function validProgress(p){return p&&typeof p==='object'&&typeof p.section==='string'&&/^(section-[a-z-]+|article-sources)$/.test(p.section)&&Number.isFinite(p.percent)&&p.percent>=0&&p.percent<=100&&Number.isFinite(p.time);}
  const resume=$('#reading-resume');
  if(resume){
    const last=stories.filter(s=>validProgress(progress[s.id])&&progress[s.id].percent>0&&progress[s.id].percent<98).sort((a,b)=>progress[b.id].time-progress[a.id].time)[0];
    if(last){resume.hidden=false;resume.innerHTML=`<p>Продолжить чтение: <a href="${last.url}#${escape(progress[last.id].section)}">${escape(last.short)} →</a> <span class="experience-small">${progress[last.id].percent}%</span></p>`;}
  }
  const reader=$('[data-reader]');
  if(reader){
    const id=reader.dataset.reader,sections=$$('[data-reading-section],#article-sources'),links=$$('.reader-aside nav a'),bar=$('.reader-progress');
    const previous=progress[id],resumeLink=$('.reader-resume');
    if(validProgress(previous)&&previous.percent>0&&previous.percent<98&&sections.some(s=>s.id===previous.section)){resumeLink.href='#'+previous.section;resumeLink.hidden=false;}
    const sizeButtons=$$('[data-reading-size]');
    const setSize=size=>{const large=size==='large';$('.story-prose').classList.toggle('reader-large',large);press(sizeButtons,sizeButtons.find(b=>b.dataset.readingSize===(large?'large':'normal')));};
    setSize(read('tonko-reading-size-v1','normal'));sizeButtons.forEach(b=>b.addEventListener('click',()=>{setSize(b.dataset.readingSize);write('tonko-reading-size-v1',b.dataset.readingSize,true);}));
    let frame=false,saveTimer,latest=null;
    const update=(persist=false)=>{
      frame=false;if(!sections.length)return;
      const start=sections[0].getBoundingClientRect().top+scrollY-120,end=sections.at(-1).getBoundingClientRect().bottom+scrollY-innerHeight;
      const percent=Math.round(Math.max(0,Math.min(100,(scrollY-start)/Math.max(1,end-start)*100)));
      bar.setAttribute('aria-valuenow',String(percent));bar.firstElementChild.style.transform=`scaleX(${percent/100})`;
      let current=sections[0];for(const section of sections)if(section.getBoundingClientRect().top<180)current=section;
      links.forEach(a=>{if(a.hash==='#'+current.id)a.setAttribute('aria-current','true');else a.removeAttribute('aria-current');});
      if(persist&&scrollY>30){latest={section:current.id,percent,time:Date.now()};clearTimeout(saveTimer);saveTimer=setTimeout(()=>{progress[id]=latest;write('tonko-reading-progress-v1',progress);},250);}
    };
    addEventListener('scroll',()=>{if(!frame){frame=true;requestAnimationFrame(()=>update(true));}},{passive:true});addEventListener('resize',()=>update());
    addEventListener('pagehide',()=>{if(latest){progress[id]=latest;write('tonko-reading-progress-v1',progress);}});update();
  }
  $$('[data-quick-check]').forEach(check=>{
    const buttons=[...check.querySelectorAll('[data-answer]')];buttons.forEach(b=>b.addEventListener('click',()=>{press(buttons,b);check.querySelector('.check-feedback').textContent=(b.dataset.answer===check.dataset.quickCheck?'Верно. ':'Попробуйте ещё раз. ')+check.dataset.feedback;}));
  });

  // Static archive remains readable without JS; enhancement offers a finite, shareable timeline.
  const eraButtons=$$('[data-era]'),scenes=$$('.archive-scene');
  if(eraButtons.length&&scenes.length){
    let index=0;const controls=$('.archive-controls');controls.hidden=false;
    function showEra(i,animate=true,changeUrl=true){
      index=Math.max(0,Math.min(i,scenes.length-1));scenes.forEach((el,n)=>el.hidden=n!==index);press(eraButtons,eraButtons[index]);
      if(animate&&!reduced.matches)scenes[index].animate([{opacity:0,transform:'translateY(12px)'},{opacity:1,transform:'translateY(0)'}],{duration:380,easing:'cubic-bezier(.16,1,.3,1)'});
      $('[data-era-prev]').disabled=index===0;$('[data-era-next]').disabled=index===scenes.length-1;
      $('#era-status').textContent=`${index+1} / ${scenes.length} · ${eraButtons[index].querySelector('span').textContent}`;
      if(changeUrl){const url=new URL(location.href);url.hash=scenes[index].id;history.replaceState(null,'',url);}
      // Move only the horizontal rail, keeping the reader's vertical scroll position.
      const rail=$('.archive-years'),button=eraButtons[index];rail.scrollTo({left:button.offsetLeft-rail.offsetLeft-rail.clientWidth/2+button.clientWidth/2,behavior:'auto'});
    }
    const fromHash=()=>{const i=scenes.findIndex(s=>'#'+s.id===location.hash);if(i>=0)showEra(i,false,false);};
    eraButtons.forEach((b,i)=>b.addEventListener('click',()=>showEra(i)));
    $('[data-era-prev]').onclick=()=>showEra(index-1);$('[data-era-next]').onclick=()=>showEra(index+1);
    showEra(0,false,false);fromHash();addEventListener('hashchange',fromHash);
  }

  const canvas=$('#detail-canvas');
  if(canvas){
    const img=$('#detail-image'),zoom=$('#detail-zoom'),thumbs=$$('[data-detail]');
    let scale=1,x=0,y=0,pointer=null,media=[],selected=0;
    function bounds(){const cw=canvas.clientWidth,ch=canvas.clientHeight,w=Math.min(cw,ch*(img.naturalWidth||1)/(img.naturalHeight||1)),h=w*(img.naturalHeight||1)/(img.naturalWidth||1);return {x:Math.max(0,(w*scale-cw)/2),y:Math.max(0,(h*scale-ch)/2),w};}
    function render(){const b=bounds();x=Math.max(-b.x,Math.min(b.x,x));y=Math.max(-b.y,Math.min(b.y,y));img.style.transform=`translate(${x}px,${y}px) scale(${scale})`;canvas.classList.toggle('zoomed',scale>1.01);zoom.value=String(scale);$('#detail-zoom-value').textContent=scale.toLocaleString('ru-RU',{maximumFractionDigits:2})+'×';}
    function reset(){scale=1;x=y=0;render();}
    function loaded(){const b=bounds();zoom.max=String(Math.max(1,Math.min(3,Math.floor(img.naturalWidth/Math.max(1,b.w)*100)/100)));scale=Math.min(scale,Number(zoom.max));render();$('#detail-status').textContent=`Исходник: ${img.naturalWidth} × ${img.naturalHeight} px. Максимум ${Number(zoom.max).toLocaleString('ru-RU')}×.`;}
    img.addEventListener('load',loaded);img.addEventListener('error',()=>{$('#detail-status').textContent='Не удалось загрузить снимок. Выберите другой или обновите страницу.';});if(img.complete&&img.naturalWidth)loaded();
    zoom.addEventListener('input',()=>{scale=Number(zoom.value);render();});
    $('#detail-reset').onclick=reset;
    $('#detail-closer').onclick=()=>{scale=Math.min(Number(zoom.max),2.2);const b=bounds();y=-b.y*.35;x=0;render();canvas.focus({preventScroll:true});};
    canvas.addEventListener('pointerdown',e=>{if(scale<=1.01||e.button>0)return;pointer={id:e.pointerId,sx:e.clientX,sy:e.clientY,x,y};canvas.setPointerCapture(e.pointerId);canvas.classList.add('dragging');});
    canvas.addEventListener('pointermove',e=>{if(pointer?.id!==e.pointerId)return;x=pointer.x+e.clientX-pointer.sx;y=pointer.y+e.clientY-pointer.sy;render();});
    const release=()=>{pointer=null;canvas.classList.remove('dragging');};canvas.addEventListener('pointerup',release);canvas.addEventListener('pointercancel',release);canvas.addEventListener('lostpointercapture',release);canvas.addEventListener('blur',release);
    canvas.addEventListener('keydown',e=>{
      if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-','0'].includes(e.key))return;e.preventDefault();
      if(e.key==='0'){reset();return;}if(['+','='].includes(e.key))scale=Math.min(Number(zoom.max),scale+.15);if(e.key==='-')scale=Math.max(1,scale-.15);
      if(e.key==='ArrowLeft')x-=35;if(e.key==='ArrowRight')x+=35;if(e.key==='ArrowUp')y-=35;if(e.key==='ArrowDown')y+=35;render();
    });
    async function choose(i,updateUrl=true){
      const button=thumbs[i],p=media.find(p=>p.id===button?.dataset.detail);if(!p)return;selected=i;release();reset();press(thumbs,button);
      img.src=p.image;img.alt=p.alt;$('#detail-title').textContent=button.dataset.detailTitle;$('#detail-description').textContent=button.dataset.detailDescription;$('.detail-controls>.portal-eyebrow').textContent=`0${i+1} / 0${thumbs.length}`;
      $('#detail-credit').innerHTML=`<a href="${escape(p.source)}" target="_blank" rel="noopener">${escape(p.author)} · источник фотографии ↗</a>`;
      if(updateUrl){const url=new URL(location.href);url.searchParams.set('photo',p.id);history.replaceState(null,'',url);}
    }
    fetch('data/editorial-media.json').then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{media=data;const id=new URLSearchParams(location.search).get('photo'),i=thumbs.findIndex(b=>b.dataset.detail===id);if(i>=0)choose(i,false);thumbs.forEach((b,i)=>b.addEventListener('click',()=>choose(i)));}).catch(()=>{$('#detail-status').textContent='Подборка временно не загрузилась. Текущую фотографию можно рассмотреть; обновите страницу для выбора остальных.';});
    if('ResizeObserver' in window)new ResizeObserver(()=>{if(img.naturalWidth)loaded();}).observe(canvas);
  }
  const comparison=$('#compare-position');
  if(comparison){comparison.addEventListener('input',()=>{$('#photo-comparison').style.setProperty('--split',comparison.value+'%');$('#compare-position-value').textContent=comparison.value+'%';});}
  $$('[data-gallery-density]').forEach(b=>b.addEventListener('click',()=>{press($$('[data-gallery-density]'),b);$('#editorial-gallery')?.classList.toggle('gallery-large',b.dataset.galleryDensity==='large');$$('#editorial-gallery img[srcset]').forEach(img=>img.sizes=b.dataset.galleryDensity==='large'?'(max-width:540px) 100vw, 50vw':'(max-width:540px) 50vw, (max-width:1100px) 33vw, 25vw');}));

  // Decorative motion is optional. No initial CSS hiding, timers, scroll hijacking or autoplay.
  if(!reduced.matches&&'IntersectionObserver' in window&&Element.prototype.animate){
    const observer=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(!entry.isIntersecting)return;observer.unobserve(entry.target);entry.target.animate([{opacity:.25,transform:'translateY(20px)'},{opacity:1,transform:'translateY(0)'}],{duration:550,easing:'cubic-bezier(.16,1,.3,1)'});});},{threshold:.12});
    $$('[data-reveal]').forEach(el=>observer.observe(el));reduced.addEventListener('change',e=>{if(e.matches){observer.disconnect();document.getAnimations().forEach(a=>a.finish());}});
  }
})();
