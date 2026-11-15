// Real provider playback, without mocked responses. Local server: port 4185.
async (page) => {
  const c = await page.context().browser().newContext({viewport:{width:1365,height:1000}});
  const p = await c.newPage(), errors = [], checks = [], samples = [];
  const check = (ok, label) => { if (!ok) throw new Error(label); checks.push(label); };
  p.on('pageerror', e => errors.push(e.message));
  try {
    await p.goto('http://127.0.0.1:4185/videos.html', {waitUntil:'networkidle'});
    for (const id of ['1100274499','1102160026','1104089394']) {
      const loaded = p.waitForEvent('framenavigated', {predicate:f=>f.url().startsWith('https://player.vimeo.com/video/'+id),timeout:40000});
      await p.locator('.video-watch-button[data-video-play="vimeo-'+id+'"]').click();
      const frame = await loaded;
      await frame.waitForFunction(()=>{const v=document.querySelector('video');return v&&!v.paused&&v.currentTime>2&&v.readyState>=3;}, null, {timeout:40000});
      const first = await frame.evaluate(()=>{const v=document.querySelector('video');return{time:v.currentTime,duration:v.duration,ready:v.readyState,width:v.videoWidth,muted:v.muted,volume:v.volume};});
      await p.waitForTimeout(1500);
      const last = await frame.evaluate(()=>{const v=document.querySelector('video');return{time:v.currentTime,paused:v.paused,ready:v.readyState};});
      samples.push({id,first,last});
      check(last.time>first.time&&!last.paused, 'Actual video advances: '+id);
      check(first.width>0&&first.ready>=3&&last.ready>=3, 'Decoded video frames available: '+id);
      await p.screenshot({path:'C:/Users/big-a/Documents/Codex_мои_программы/TOHKO/qa/live-vimeo-'+id+'.png'});
      await p.locator('#video-stop').click();
      check(await p.locator('#video-screen iframe').count()===0, 'Player is removed on close: '+id);
    }
    await p.locator('#video-provider').selectOption('vimeo');
    check(await p.locator('[data-video-card]:visible').count()===3, 'Without YouTube filter contains three films');
    await p.locator('#video-language').selectOption('ru');
    check(await p.locator('#video-empty').isVisible(), 'Combined provider and language filter has a useful empty state');
    await p.locator('#video-reset').click();
    check(await p.locator('[data-video-card]:visible').count()===14, 'Reset restores the complete library');

    await p.goto('http://127.0.0.1:4185/lookbook.html', {waitUntil:'networkidle'});
    check(await p.locator('#photo-campaign-red img').evaluate(img=>img.complete&&img.naturalWidth>0), 'Supplied photo loads in the gallery');
    await p.locator('[data-gallery-filter="men"]').click();
    await p.locator('[data-feature-photo="campaign-red"]').click();
    check(await p.locator('#editorial-lightbox').evaluate(d=>d.open), 'Featured photo opens even after choosing a different theme');
    check(await p.locator('#editorial-full-image').evaluate(img=>img.complete&&img.naturalWidth===1200), 'Lightbox shows the full 1200px original');
    await p.keyboard.press('Escape');
    check(await p.locator('[data-feature-photo]').evaluate(a=>document.activeElement===a), 'Closing lightbox restores focus to its cover');
    await p.screenshot({path:'C:/Users/big-a/Documents/Codex_мои_программы/TOHKO/qa/v6-gallery-desktop.png'});
    for (const width of [390,320]) {
      await p.setViewportSize({width,height:844});
      for (const file of ['index.html','lookbook.html','videos.html']) {
        await p.goto('http://127.0.0.1:4185/'+file, {waitUntil:'networkidle'});
        check(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth), 'No horizontal overflow at '+width+'px: '+file);
        await p.screenshot({path:'C:/Users/big-a/Documents/Codex_мои_программы/TOHKO/qa/v6-'+width+'-'+file+'.png'});
      }
    }
    await p.setViewportSize({width:1365,height:1000}); await p.goto('http://127.0.0.1:4185/');
    await p.screenshot({path:'C:/Users/big-a/Documents/Codex_мои_программы/TOHKO/qa/v6-home-desktop.png'});
    check(errors.length===0, 'No page errors during real playback and photo viewing');
    return {passed:checks.length,checks,samples};
  } finally {await c.close();}
}
