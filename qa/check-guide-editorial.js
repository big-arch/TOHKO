// Pass this file to Playwright browser_run_code_unsafe. No external requests.
async page => {
  const base='http://127.0.0.1:4185/',checks=[],errors=[];
  const context=await page.context().browser().newContext({viewport:{width:1365,height:900},reducedMotion:'reduce'});
  const assert=(ok,label)=>{if(!ok)throw Error(label);checks.push(label);};
  await context.route('**/*',r=>r.request().url().startsWith(base)?r.continue():r.abort());
  const p=await context.newPage();p.on('pageerror',e=>errors.push(e.message));
  try {
    for(const width of [1365,768,390,320]){
      await p.setViewportSize({width,height:900});
      await p.goto(base+'guide.html',{waitUntil:'domcontentloaded'});
      assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'guide fits '+width);
      assert(await p.locator('.studio-clip video').evaluateAll(v=>v.every(e=>!e.src&&e.paused&&!e.loop)),'no autoplay or default loop with reduced motion '+width);
      await p.locator('input[name="occasion"][value="sport"]').focus();await p.keyboard.press('Space');
      assert((await p.locator('#studio-result h3').textContent()).includes('легинсы'),'keyboard selection changes result '+width);
      assert(await p.locator('#studio-result>a').getAttribute('href')==='leggings.html','sport has a relevant next step '+width);
      await p.locator('input[name="look"][value="pattern"]').focus();await p.keyboard.press('Space');
      assert((await p.locator('#studio-result h3').textContent()).includes('легинсы'),'sport result survives decorative preference '+width);
      await p.locator('#studio-save').click();await p.reload({waitUntil:'domcontentloaded'});
      assert(await p.locator('input[name="occasion"][value="sport"]').isChecked(),'saved choice restored '+width);
      await p.locator('#studio-picker button[type="reset"]').click();
      await p.waitForFunction(()=>document.querySelector('#studio-result h3').textContent==='Прозрачная пара');
      assert(await p.evaluate(()=>localStorage.getItem('tonko-guide-profile-v1')===null),'reset clears saved profile '+width);
      if(width<=700){await p.locator('.studio-result-jump').click();assert(p.url().includes('#studio-choice-preview'),'mobile result jump '+width);}
      for(const key of ['surface','den','pattern']){
        const button=p.locator(`[data-compare="${key}"]`);await button.focus();await p.keyboard.press('Enter');
        assert(await button.getAttribute('aria-pressed')==='true','comparison keyboard mode '+key+' '+width);
        await p.locator('#studio-compare-stage').scrollIntoViewIfNeeded();
        await p.waitForFunction(()=>[...document.querySelectorAll('#studio-compare-stage img')].every(i=>i.complete&&i.naturalWidth>0));
        assert(await p.locator('#compare-credits a').count()===2,'photo credits '+key+' '+width);
      }
      await p.locator('#photo-boundary').focus();await p.keyboard.press('End');
      assert(await p.locator('#photo-boundary-value').textContent()==='100%','range reaches right edge '+width);
      await p.keyboard.press('Home');
      assert(await p.locator('#compare-front').evaluate(e=>e.style.clipPath)==='inset(0px 100% 0px 0px)','range reveals entire second photo '+width);
      await p.locator('#compare-reset').click();
      assert(await p.locator('#photo-boundary').inputValue()==='50','comparison reset '+width);
      const handle=await p.locator('#compare-line span').boundingBox(),stage=await p.locator('#studio-compare-stage').boundingBox();
      await p.mouse.move(handle.x+handle.width/2,handle.y+handle.height/2);await p.mouse.down();
      await p.mouse.move(stage.x+stage.width*.75,handle.y+handle.height/2);await p.mouse.up();
      assert(Math.abs(Number(await p.locator('#photo-boundary').inputValue())-75)<=1,'photo handle drags directly '+width);
      const part=p.locator('[data-part]').last();await part.click();
      assert(await part.getAttribute('aria-pressed')==='true','existing anatomy still works '+width);
      await p.locator('#care-checklist input').first().check();
      assert((await p.locator('#care-check-count').textContent()).includes('1 из'),'care checklist still works '+width);
      await p.locator('#quiz-options button').first().click();await p.locator('#quiz-next').click();
      assert((await p.locator('#quiz-position').textContent()).includes('2 /'),'quiz still progresses '+width);
    }
    const permutations=await p.evaluate(()=>{
      let n=0;
      for(const occasion of ['daily','evening','under','sport'])for(const look of ['sheer','opaque','pattern'])for(const weather of ['inside','mild','cold'])for(const priority of ['waist','seams','wear']){
        const result=TonkoGuide.recommend({occasion,look,weather,priority});
        if(!result.title||!result.photo||result.tips.some(t=>!t)||JSON.stringify(result).includes('undefined'))throw Error('Incomplete recommendation');n++;
      }return n;
    });assert(permutations===108,'all 108 choice combinations return complete guidance');
    await p.locator('.studio-video-start').first().click();
    await p.waitForFunction(()=>/не загрузилось|недоступен/.test(document.querySelector('.studio-video-status').textContent));
    assert(await p.locator('.studio-video-start').first().isVisible(),'blocked video offers retry without navigation');
    for(const width of [1365,390,320]){
      await p.setViewportSize({width,height:900});
      for(const topic of ['light','patterns','construction','product-card','making','archive']){
        await p.goto(base+'read-'+topic+'.html',{waitUntil:'domcontentloaded'});
        assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),topic+' fits '+width);
        assert(await p.locator('.editorial-practice li').count()===3,topic+' original practical continuation '+width);
        const links=p.locator('.editorial-update-card h3 a');assert(await links.count()>0,topic+' topical full reviews '+width);
        const a=links.first();await a.click();await p.locator('.news-reader[open]').waitFor();
        assert(p.url().includes('read-'+topic+'.html?news='),topic+' reads onsite '+width);
        assert(await p.locator('.news-reader .reader-copy section').count()>=2,topic+' full Russian content '+width);
        await p.waitForFunction(()=>{const i=document.querySelector('.news-reader[open] img');return i&&i.complete&&i.naturalWidth>0;});
        assert(await p.locator('.news-reader').evaluate(e=>e.scrollWidth<=e.clientWidth+1),topic+' reader fits '+width);
        await p.keyboard.press('Escape');assert(await a.evaluate(e=>e===document.activeElement),topic+' focus returns '+width);
      }
    }
    await p.goto(base+'journal.html',{waitUntil:'domcontentloaded'});
    assert(await p.locator('.journal-row .editorial-update-date').count()===6,'journal shows all six real update dates');
    await p.goto(base+'read-light.html',{waitUntil:'domcontentloaded'});
    const id=await p.locator('[data-editorial-news]').first().getAttribute('data-editorial-news');
    await p.goto(base+'read-light.html?news='+id,{waitUntil:'domcontentloaded'});await p.locator('.news-reader[open]').waitFor();
    assert((await p.locator('#reader-title').textContent()).length>10,'shared editorial deep link opens full review');
    assert(errors.length===0,'no page script errors');
    const plain=await page.context().browser().newContext({javaScriptEnabled:false});
    try{
      await plain.route('**/*',r=>r.request().url().startsWith(base)?r.continue():r.abort());
      const q=await plain.newPage();await q.goto(base+'read-light.html');
      await q.locator('.editorial-update-card h3 a').first().click();
      assert(q.url().includes('news.html#story-'),'without JavaScript article opens full local fallback');
      assert(await q.locator('#story-'+id+' section').count()>=2,'fallback contains full text');
    }finally{await plain.close();}
    return {passed:checks.length,choiceCombinations:permutations,errors};
  }finally{await context.close();}
}
