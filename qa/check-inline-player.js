// Run with Playwright browser_run_code_unsafe(filename). Local server: port 4185.
// Mock only YouTube responses: these checks prove integration, not media availability.
async (page) => {
  const base = 'http://127.0.0.1:4185/';
  const browser = page.context().browser();
  const checks = [], contexts = [], errors = [];
  const check = (ok, label) => { if (!ok) throw new Error(label); checks.push(label); };
  const mock = `
    window.__players = [];
    window.YT = { Player: class {
      constructor(frame, options) {
        this.frame = frame; this.events = options.events; this.state = -1;
        window.__players.push(this);
        if (!window.__silentReady) queueMicrotask(() => this.emit('onReady'));
      }
      getPlayerState() { return this.state; }
      destroy() { this.destroyed = true; this.frame.remove(); }
      emit(name, data) {
        if (name === 'onStateChange') this.state = data;
        this.events[name]?.({target: this, data});
      }
    }};
    window.onYouTubeIframeAPIReady?.();`;
  const create = async (options = {}) => {
    const c = await browser.newContext({viewport:{width:1365,height:900}, ...options});
    contexts.push(c);
    await c.route('https://www.youtube-nocookie.com/embed/**', r => r.fulfill({contentType:'text/html',body:'<!doctype html><title>Test iframe</title>'}));
    const p = await c.newPage(); p.on('pageerror', e => errors.push(e.message));
    return p;
  };
  const countPlayers = (p, n) => p.waitForFunction(n => window.__players?.length === n, n);
  const emit = (p, name, data) => p.evaluate(({name,data}) => window.__players.at(-1).emit(name,data), {name,data});
  let release;
  try {
    const p = await create();
    const requests = [];
    p.on('request', r => { if (/youtube|googlevideo|ytimg/.test(r.url())) requests.push(r.url()); });
    await p.route('https://www.youtube.com/iframe_api', r => r.fulfill({contentType:'application/javascript',body:mock}));
    await p.goto(base+'videos.html', {waitUntil:'networkidle'});
    check(requests.length === 0, 'No YouTube connections before a play click');
    check(await p.locator('.video-watch-button:visible').count() === 11, 'All 11 cards offer Watch on site');
    check(!(await p.locator('#video-original').isVisible()), 'Original link is in collapsed source details');
    await p.locator('.video-watch-button').nth(1).click(); await countPlayers(p, 1);
    const src = await p.locator('#video-screen iframe').evaluate(frame => {const url=new URL(frame.src);return {pathname:url.pathname,enablejsapi:url.searchParams.get('enablejsapi'),origin:url.searchParams.get('origin')};});
    check(src.pathname.endsWith('/gkbMiMVNwyg'), 'Card plays the selected video');
    check(p.url().startsWith(base+'videos.html?video=') && p.context().pages().length === 1, 'Watching stays on TONKO without a new tab');
    check(src.enablejsapi === '1' && src.origin === 'http://127.0.0.1:4185', 'Embed identifies the site and enables the official API');
    check(await p.locator('#video-screen iframe').getAttribute('allowfullscreen') !== null && await p.locator('#video-screen iframe').getAttribute('referrerpolicy') === 'strict-origin-when-cross-origin', 'Native fullscreen and Referer policy are enabled');
    await emit(p, 'onStateChange', 1);
    check(!(await p.locator('#video-playback-status').isVisible()), 'Playback clears the loading hint');
    await emit(p, 'onAutoplayBlocked');
    check((await p.locator('#video-playback-status').innerText()).includes('нажмите ▶ внутри плеера'), 'Autoplay block directs the reader to native play');
    await emit(p, 'onError', 5);
    await emit(p, 'onStateChange', 2);
    check(await p.locator('#video-retry').isVisible(), 'Playback error offers an in-page retry');
    await p.locator('#video-retry').click(); await countPlayers(p,2);
    check(await p.locator('#video-screen iframe').count() === 1 && await p.evaluate(()=>window.__players[0].destroyed), 'Retry replaces the old player and keeps one iframe');
    await emit(p, 'onError', 150);
    check((await p.locator('#video-playback-status').innerText()).includes('Причина указана внутри плеера'), 'Restricted playback keeps the native YouTube explanation');
    await emit(p, 'onError', 100);
    check(!(await p.locator('#video-retry').isVisible()) && (await p.locator('#video-playback-status').innerText()).includes('закрытым'), 'Removed or private video shows a specific message');
    await emit(p, 'onError', 153);
    check((await p.locator('#video-playback-status').innerText()).includes('адрес'), 'Missing client identity shows a specific message');
    await p.locator('#video-stop').click();
    check(await p.locator('#video-screen iframe').count() === 0 && await p.locator('#video-screen button').evaluate(e=>e===document.activeElement), 'Close stops the iframe and restores keyboard focus');
    await emit(p, 'onError', 5);
    check(!(await p.locator('#video-playback-status').isVisible()), 'Late events from a closed player cannot alter the poster');
    await p.locator('[data-video-topic="asmr"]').click();
    await p.locator('#video-next').click(); await countPlayers(p,3);
    check((await p.locator('#video-screen iframe').getAttribute('src')).includes('QpApOq2Q0l8'), 'Next respects the selected topic');
    await p.locator('#video-next').click(); await countPlayers(p,4);
    check((await p.locator('#video-screen iframe').getAttribute('src')).includes('tSa26mVW5gM') && await p.locator('#video-screen iframe').count() === 1, 'Next replaces playback without leaving the page');
    await p.goto(base+'videos.html?video=tSa26mVW5gM', {waitUntil:'networkidle'});
    check(await p.locator('#video-screen iframe').count() === 0 && await p.locator('#video-screen button').getAttribute('data-video-play') === 'tSa26mVW5gM', 'Shared link selects a video without unsolicited autoplay');
    await p.setViewportSize({width:320,height:740});
    await p.locator('.video-watch-button').first().click(); await countPlayers(p,1);
    const bounds = await p.locator('#video-screen').boundingBox();
    check(bounds.width >= 200 && bounds.height >= 200 && await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth), '320px layout fits the player without horizontal scrolling');
    await p.locator('#video-stop').click();
    await p.locator('#video-library').scrollIntoViewIfNeeded();
    await p.screenshot({path:'C:/Users/big-a/Documents/Codex_мои_программы/TOHKO/qa/player-mobile-cards.png'});
    await p.setViewportSize({width:1365,height:900}); await p.goto(base+'videos.html', {waitUntil:'networkidle'});
    await p.screenshot({path:'C:/Users/big-a/Documents/Codex_мои_программы/TOHKO/qa/player-desktop.png'});

    const race = await create();
    const gate = new Promise(resolve => {release=resolve;});
    await race.route('https://www.youtube.com/iframe_api', async r => {await gate; await r.fulfill({contentType:'application/javascript',body:mock});});
    await race.goto(base+'videos.html', {waitUntil:'networkidle'});
    await race.locator('#video-screen button').click(); await race.locator('#video-stop').click();
    release(); await race.waitForFunction(()=>!!window.YT?.Player);
    check(await race.locator('iframe').count() === 0 && await race.evaluate(()=>window.__players.length===0), 'Closing during SDK loading never resurrects playback');
    await race.locator('#video-screen button').click(); await countPlayers(race,1);
    check(await race.locator('#video-screen iframe').count() === 1, 'Player can reopen after closing during API load');

    const unavailable = await create();
    await unavailable.route('https://www.youtube.com/iframe_api', r => r.abort('failed'));
    await unavailable.goto(base+'videos.html', {waitUntil:'networkidle'});
    await unavailable.locator('#video-screen button').click();
    await unavailable.waitForFunction(()=>document.querySelector('#video-playback-status').textContent.includes('Используйте кнопки'));
    check(await unavailable.locator('#video-screen iframe').count()===1 && await unavailable.locator('#video-retry').isVisible(), 'API failure preserves the native iframe and offers retry');

    const slow = await create();
    await slow.addInitScript(()=>{window.__silentReady=true;});
    await slow.route('https://www.youtube.com/iframe_api', r => r.fulfill({contentType:'application/javascript',body:mock}));
    await slow.goto(base+'videos.html', {waitUntil:'networkidle'}); await slow.clock.install();
    await slow.locator('#video-screen button').click(); await countPlayers(slow,1); await slow.clock.fastForward(19000);
    check((await slow.locator('#video-playback-status').innerText()).includes('долго загружается') && await slow.locator('#video-retry').isVisible(), 'A stalled iframe gets a recoverable loading message');
    await slow.locator('#video-stop').click(); await slow.clock.fastForward(20000);
    check(!(await slow.locator('#video-playback-status').isVisible()), 'Closing clears outstanding loading timers');

    const plain = await create({javaScriptEnabled:false});
    await plain.goto(base+'videos.html'); await plain.locator('.video-card .video-source summary').first().click();
    check(await plain.locator('.video-card .video-source a').nth(1).isVisible() && await plain.locator('iframe').count()===0, 'Source links remain available without JavaScript');
    check(errors.length===0, 'No uncaught page errors in all scenarios');
    return {passed:checks.length,checks};
  } finally {release?.(); for (const c of contexts) await c.close();}
}
