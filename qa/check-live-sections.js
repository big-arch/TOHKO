// Run as the function passed to Playwright browser_run_code_unsafe (filename).
// Uses an isolated context. External services, including the assistant, are blocked.
async (page) => {
  const base='http://127.0.0.1:4185/';
  const browser=page.context().browser();
  const context=await browser.newContext({viewport:{width:1365,height:900},reducedMotion:'reduce'});
  const errors=[],checks=[];
  const assert=(value,label)=>{if(!value)throw Error(label);checks.push(label);};
  await context.route('**/*',r=>r.request().url().startsWith(base)?r.continue():r.abort());
  const p=await context.newPage();p.on('pageerror',e=>errors.push(e.message));
  try {
    let release;
    const loading=new Promise(resolve=>{release=resolve;});
    await context.route('**/data/editorial-media.json',async r=>{await loading;await r.continue();});
    await p.goto(base+'lookbook.html',{waitUntil:'domcontentloaded'});
    assert(await p.locator('[data-gallery-filter="updates"]').isDisabled(),'filter waits for gallery data');
    assert(await p.locator('#editorial-gallery').getAttribute('aria-busy')==='true','gallery exposes loading state');
    release();await p.locator('#editorial-gallery .gallery-open').first().waitFor();
    assert(await p.locator('[data-gallery-filter="updates"]').isEnabled(),'filter enabled after gallery data');
    await p.locator('[data-gallery-filter="updates"]').click();
    const photoCount=JSON.parse(await p.locator('#live-seed').textContent()).photos.length;
    assert(await p.locator('#editorial-gallery .gallery-item').count()===photoCount,'first filter click after slow load is retained');
    await context.unroute('**/data/editorial-media.json');
    for(const width of [1365,390,320]){
      await p.setViewportSize({width,height:900});
      for(const file of ['index.html','journal.html','men.html','lookbook.html']){
        await p.goto(base+file,{waitUntil:'domcontentloaded'});
        const data=JSON.parse(await p.locator('#live-seed').textContent());
        assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),file+' fits '+width);
        if(file!=='lookbook.html'){
          const section=p.locator('[data-live-feed]');
          await section.locator('.live-filters:not([hidden])').waitFor();
          const audience=file==='men.html'?data.items.filter(i=>i.men):data.items;
          assert(await section.locator('.live-item').count()===Math.min(6,audience.length),file+' initial rows '+width);
          const button=section.locator('[data-live-filter="translated"]');
          await button.focus();await p.keyboard.press('Enter');
          assert(await button.getAttribute('aria-pressed')==='true',file+' keyboard filter '+width);
          const ready=audience.filter(i=>i.language!=='ru');
          assert(await section.locator('.live-item').count()===Math.min(6,ready.length),file+' ready count '+width);
          assert(await section.locator('.live-item h3 a').evaluateAll(a=>a.every(e=>e.getAttribute('href').startsWith('news.html#story-'))),file+' full articles stay onsite '+width);
          const articleLink=section.locator('.live-item h3 a').first();
          await articleLink.click();await p.locator('.news-reader[open]').waitFor();
          assert(p.url().split('?')[0]===base+file,file+' opens reader without leaving page '+width);
          assert(await p.locator('.news-reader .reader-copy section').count()>=2,file+' full Russian sections '+width);
          assert(await p.locator('.news-reader .reader-excerpt').getAttribute('lang')==='ru',file+' Russian introduction '+width);
          assert(await p.locator('.news-reader .reader-source').count()>0,file+' source attribution retained '+width);
          await p.waitForFunction(()=>{const i=document.querySelector('.news-reader[open] .reader-visual img');return !i||(i.complete&&i.naturalWidth>0);});
          assert(await p.locator('.news-reader').evaluate(e=>e.scrollWidth<=e.clientWidth+1),file+' reader fits '+width);
          await p.keyboard.press('Escape');
          assert(await articleLink.evaluate(e=>e===document.activeElement),file+' reader focus restored '+width);
          await section.locator('[data-live-filter="ru"]').click();
          assert(await section.locator('.live-item h3 a').evaluateAll(a=>a.every(e=>e.getAttribute('href').startsWith('news.html#story-')&&!e.target)),file+' Russian source cards also stay onsite '+width);
          await section.locator('[data-live-filter="all"]').click();
          const more=section.locator('.live-more');
          if(await more.isVisible()){await more.click();assert(await section.locator('.live-item').count()>6,file+' more sources '+width);}
        }else{
          const filter=p.locator('[data-gallery-filter="updates"]');await filter.click();
          assert(await p.locator('#editorial-gallery .gallery-item').count()===data.photos.length,'new gallery count '+width);
          const first=p.locator('#editorial-gallery .gallery-open').first();await first.scrollIntoViewIfNeeded();
          await p.waitForFunction(()=>{const i=document.querySelector('#editorial-gallery img');return i&&i.complete&&i.naturalWidth>0;});
          await first.click();await p.locator('#editorial-lightbox[open]').waitFor();
          await p.waitForFunction(()=>{const i=document.querySelector('#editorial-full-image');return i&&i.complete&&i.naturalWidth>0;});
          assert(await p.locator('#editorial-photo-source').getAttribute('href')===data.photos[0].source,'photo original credit '+width);
          const title=await p.locator('#editorial-photo-title').textContent();await p.keyboard.press('ArrowRight');
          assert(await p.locator('#editorial-photo-title').textContent()!==title,'photo keyboard next '+width);
          await p.keyboard.press('Escape');
          assert(await first.evaluate(e=>e===document.activeElement),'photo focus restored '+width);
        }
        assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),file+' filtered fits '+width);
      }
    }
    await p.setViewportSize({width:1365,height:900});
    await p.goto(base+'journal.html',{waitUntil:'domcontentloaded'});
    await p.locator('.live-filters:not([hidden])').waitFor();
    const firstId=await p.locator('.live-item').first().getAttribute('data-live-item');
    const changed=JSON.parse(await p.locator('#live-seed').textContent());
    changed.checkedAt=new Date().toISOString();
    changed.items.unshift({...changed.items[0],id:'qa-incoming',title:'Проверка нового материала на русском'});
    await context.route('**/data/live-feed.json?*',r=>r.fulfill({json:changed}));
    await p.evaluate(()=>window.dispatchEvent(new Event('visibilitychange')));
    await p.locator('.live-refresh:not([hidden])').waitFor();
    assert(await p.locator('.live-item').first().getAttribute('data-live-item')===firstId,'incoming update does not replace reading position');
    await p.locator('.live-refresh').click();
    assert(await p.locator('.live-item').first().getAttribute('data-live-item')==='qa-incoming','incoming update applies on request');
    assert(await p.locator('[data-live-filter="all"]').evaluate(e=>e===document.activeElement),'incoming update restores focus');
    await context.unroute('**/data/live-feed.json?*');
    const deepId=changed.items[1].id;
    await p.goto(base+'journal.html?news='+deepId,{waitUntil:'domcontentloaded'});
    await p.locator('.news-reader[open]').waitFor();
    assert(await p.locator('.news-reader .reader-copy section').count()>=2,'direct article link opens complete reader');
    await p.keyboard.press('Escape');
    await p.goto(base+'journal.html',{waitUntil:'domcontentloaded'});await p.locator('.live-section').scrollIntoViewIfNeeded();
    await p.screenshot({path:'C:/Users/big-a/Documents/Codex_мои_программы/TOHKO/qa/autonomy-journal-desktop.png'});
    await p.setViewportSize({width:390,height:844});
    await p.goto(base+'lookbook.html?filter=updates#photo-collection',{waitUntil:'domcontentloaded'});
    await p.locator('[data-gallery-filter="updates"]').click();await p.locator('#editorial-gallery').scrollIntoViewIfNeeded();
    await p.screenshot({path:'C:/Users/big-a/Documents/Codex_мои_программы/TOHKO/qa/autonomy-gallery-mobile.png'});
    assert(errors.length===0,'no browser JavaScript errors');
  }finally{await context.close();}
  const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
  try {
    const q=await nojs.newPage();
    for(const file of ['index.html','journal.html','men.html','lookbook.html']){
      await q.goto(base+file,{waitUntil:'domcontentloaded'});
      assert(await q.locator(file==='lookbook.html'?'.live-photos img':'.live-item').count()>=3,file+' readable without JavaScript');
      if(file!=='lookbook.html'){
        const href=await q.locator('.live-item h3 a').first().getAttribute('href');
        await q.goto(base+href,{waitUntil:'domcontentloaded'});
        assert(await q.locator(':target .reader-copy section').count()>=2,file+' full article readable without JavaScript');
      }
    }
  }finally{await nojs.close();}
  return {checks:checks.length,passed:checks,errors};
}
