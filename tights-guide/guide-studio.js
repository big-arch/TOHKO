/* Real photographs and user-controlled native clips; no artificial DEN rendering. */
(() => {
  'use strict';
  const seed=document.getElementById('guide-studio-data');if(!seed)return;
  let config;try{config=JSON.parse(seed.textContent);}catch{return;}
  const $=id=>document.getElementById(id),form=$('studio-picker');if(!form)return;
  const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e;};
  const options={occasion:['daily','evening','under','sport'],look:['sheer','opaque','pattern'],weather:['inside','mild','cold'],priority:['waist','seams','wear']};
  const state=()=>Object.fromEntries(Object.keys(options).map(k=>[k,new FormData(form).get(k)]));
  const safeState=value=>value&&Object.entries(options).every(([k,allowed])=>allowed.includes(value[k]));
  const priorities={waist:'Присядьте и наклонитесь: пояс должен удерживать изделие без болезненного давления и постоянного поправления.',seams:'Оцените мысок, ластовицу и центральный шов именно под своей одеждой и обувью.',wear:'Проверьте усиление мыска, рекомендации по уходу и точный размер. Большое число DEN не обещает защиту от зацепок.'};
  function recommend(s){
    if(s.occasion==='sport')return {title:'Спортивные легинсы или тайтсы',photo:'nike-leggings',intro:'Для тренировки важнее свобода движения и устойчивость посадки.',tips:['Проверьте непрозрачность ткани в приседании и при наклоне.','Оцените пояс и швы в движении; уточните назначение и состав модели.',priorities[s.priority]],url:'leggings.html',link:'Разобраться в спортивных легинсах →'};
    const looks={sheer:{title:'Прозрачная пара',photo:'wolford-1',tip:'10–30 DEN — возможная отправная точка. Оцените вид на ноге: цвет, вязка и натяжение меняют прозрачность.'},opaque:{title:'Плотная матовая фактура',photo:'swedish-rib',tip:'Сравните плотный трикотаж и состав. Число DEN само по себе не измеряет тепло; шерсть, вязка и посадка тоже имеют значение.'},pattern:{title:'Рисунок как акцент',photo:'campaign-red',tip:'Посмотрите на масштаб узора издалека и вблизи. Сопоставьте его с длиной одежды и обувью.'}};
    const look=looks[s.look];
    const occasions={daily:'Для повседневного образа начните с удобной посадки.',evening:'Определите главный акцент: рисунок, прозрачность или блеск.',under:'Под брюками оцените гладкость ткани, положение двух поясов и вид над обувью.'};
    const weather={inside:'В помещении учитывайте личное ощущение тепла и время, которое проведёте в одежде.',mild:'Сравнивайте пару с одеждой и обувью, в которых собираетесь выйти.',cold:'Для прохладной улицы рассмотрите более тёплый состав или дополнительный слой. Тонкая прозрачная пара сама по себе не гарантирует тепло.'};
    return {title:look.title,photo:s.occasion==='under'?'style-nylo-white-shirt':look.photo,intro:occasions[s.occasion],tips:[look.tip,weather[s.weather],priorities[s.priority]],url:s.look==='opaque'?'lookbook.html':'lookbook.html?filter='+s.look,link:'Посмотреть реальные примеры →'};
  }
  function credit(photo,label){const a=node('a',label||photo.author+' · источник фотографии ↗');try{const u=new URL(photo.source);if(u.protocol!=='https:')return node('span',photo.author);a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';}catch{return node('span',photo.author);}return a;}
  function photo(img,key){const p=config.photos[key];if(!p||!/^assets\/[\w/.-]+$/.test(p.image))return;img.src=p.image;img.alt=p.alt;img.width=p.width;img.height=p.height;}
  function render(){
    const choice=recommend(state()),box=$('studio-result'),list=node('ul');
    choice.tips.forEach(t=>list.append(node('li',t)));
    const link=node('a',choice.link);link.href=choice.url;
    box.replaceChildren(node('p','Ваш ориентир','portal-eyebrow'),node('h3',choice.title),node('p',choice.intro),list,link);
    const figure=$('studio-choice-photo');photo(figure.querySelector('img'),choice.photo);figure.querySelector('figcaption').replaceChildren(credit(config.photos[choice.photo]));
  }
  try{const saved=JSON.parse(localStorage.getItem('tonko-guide-profile-v1'));if(safeState(saved)){for(const [name,value] of Object.entries(saved)){const input=form.querySelector(`input[name="${name}"][value="${value}"]`);if(input)input.checked=true;}$('studio-save-status').textContent='Ваш предыдущий выбор восстановлен. Можно изменить любой ответ.';}}catch{}
  form.addEventListener('change',render);form.addEventListener('submit',e=>e.preventDefault());
  $('studio-save').addEventListener('click',()=>{try{localStorage.setItem('tonko-guide-profile-v1',JSON.stringify(state()));$('studio-save-status').textContent='Сохранено. Ваш выбор останется здесь при следующем визите.';}catch{$('studio-save-status').textContent='Браузер не разрешил сохранение. Подбор продолжает работать.';}});
  form.addEventListener('reset',()=>{try{localStorage.removeItem('tonko-guide-profile-v1');}catch{}requestAnimationFrame(render);$('studio-save-status').textContent='Выбор сброшен. Попробуйте другой сценарий.';});render();
  const comparisons={
    surface:{front:'wolford-3',back:'cdr-gloss',title:'Как полотно ловит свет',note:'Слева — фактура Wolford Individual 10, справа — блеск в съёмке Cecilia de Rafael. Рассмотрите блики и участки натяжения. Различается и освещение: это примеры, а не лабораторное сравнение.',labels:['Фактура · Wolford','Блеск · Cecilia de Rafael']},
    den:{front:'wolford-1',back:'tummy',title:'10 и 20 DEN на реальных моделях',note:'Слева — Wolford Individual 10, справа — Tummy Control Top 20. У второй модели другая верхняя часть. Сравнивайте прозрачность и конструкцию отдельно: эффект нельзя объяснить только числом DEN.',labels:['10 DEN · Individual 10','20 DEN · Tummy Control Top']},
    pattern:{front:'noq-lace',back:'ss-argyle',title:'Разный ритм рисунка',note:'Кружево NOQ и геометрия Swedish Stockings по-разному распределяют акценты. Отведите границу к краю, чтобы увидеть каждый кадр целиком, затем сравните масштаб рисунка.',labels:['Кружево · NOQ','Ромбы · Swedish Stockings']}
  };
  function boundary(){const v=Math.max(0,Math.min(100,Number($('photo-boundary').value)));$('compare-front').style.clipPath=`inset(0 ${100-v}% 0 0)`;$('compare-line').style.left=v+'%';$('photo-boundary-value').value=v+'%';$('photo-boundary').setAttribute('aria-valuetext',`${v}% левой фотографии`);}
  function compare(key){const c=comparisons[key];if(!c)return;photo($('compare-front').querySelector('img'),c.front);photo($('compare-back'),c.back);$('compare-title').textContent=c.title;$('compare-note').textContent=c.note;$('compare-credits').replaceChildren(credit(config.photos[c.front],c.labels[0]+' ↗'),credit(config.photos[c.back],c.labels[1]+' ↗'));document.querySelectorAll('[data-compare]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.compare===key)));}
  document.querySelectorAll('[data-compare]').forEach(b=>b.addEventListener('click',()=>compare(b.dataset.compare)));$('photo-boundary').addEventListener('input',boundary);$('compare-reset').addEventListener('click',()=>{$('photo-boundary').value=50;boundary();});compare('surface');boundary();
  const handle=$('compare-line').querySelector('span');
  const drag=event=>{const rect=$('studio-compare-stage').getBoundingClientRect();$('photo-boundary').value=Math.round((event.clientX-rect.left)/rect.width*100);boundary();};
  handle.addEventListener('pointerdown',event=>{if(event.button!==0)return;event.preventDefault();handle.setPointerCapture(event.pointerId);drag(event);});
  handle.addEventListener('pointermove',event=>{if(handle.hasPointerCapture(event.pointerId))drag(event);});
  const endDrag=event=>{if(handle.hasPointerCapture(event.pointerId))handle.releasePointerCapture(event.pointerId);};
  handle.addEventListener('pointerup',endDrag);handle.addEventListener('pointercancel',endDrag);
  const clips=[...document.querySelectorAll('.studio-clip')],reduced=matchMedia('(prefers-reduced-motion: reduce)');
  const pauseAll=except=>clips.forEach(c=>{const v=c.querySelector('video');if(v!==except)v.pause();});
  for(const clip of clips){const video=clip.querySelector('video'),start=clip.querySelector('.studio-video-start'),loop=clip.querySelector('[data-loop]'),status=clip.querySelector('.studio-video-status');
    loop.checked=!reduced.matches;video.loop=loop.checked;video.muted=true;
    loop.addEventListener('change',()=>{video.loop=loop.checked;status.textContent=loop.checked?'Повтор включён. Остановить можно в плеере.':'Ролик остановится после одного просмотра.';});
    start.addEventListener('click',async()=>{try{pauseAll(video);if(!video.src)video.src=video.dataset.stream;else if(video.error)video.load();await video.play();start.hidden=true;status.textContent=video.loop?'Видеопетля воспроизводится без звука.':'Видео воспроизводится без звука.';}catch{start.hidden=false;start.textContent='↻ Повторить запуск';status.textContent='Видео пока не загрузилось. Повторите запуск; фотография доступна.';}});
    video.addEventListener('play',()=>{pauseAll(video);status.textContent=video.loop?'Видеопетля воспроизводится без звука.':'Видео воспроизводится без звука.';});
    video.addEventListener('pause',()=>{if(video.currentTime>0&&!video.error)status.textContent=video.ended?'Ролик завершён. Можно посмотреть ещё раз.':'Пауза. Продолжить можно в плеере.';});
    video.addEventListener('ended',()=>{status.textContent='Ролик завершён. Можно посмотреть ещё раз.';start.textContent='↻ Посмотреть ещё раз';start.hidden=false;});
    video.addEventListener('error',()=>{start.hidden=false;start.textContent='↻ Повторить запуск';status.textContent='Источник видео сейчас недоступен. Попробуйте позже.';});
    if('IntersectionObserver' in window)new IntersectionObserver(entries=>{if(!entries[0].isIntersecting)video.pause();},{threshold:0}).observe(video);
  }
  addEventListener('visibilitychange',()=>{if(document.hidden)pauseAll();});
  reduced.addEventListener('change',()=>{if(reduced.matches){pauseAll();clips.forEach(c=>{c.querySelector('video').loop=false;c.querySelector('[data-loop]').checked=false;});}});
  window.TonkoGuide={recommend};
})();
