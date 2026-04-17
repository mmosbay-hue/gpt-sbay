const p = require('puppeteer');
(async () => {
    const b = await p.launch({ headless: 'new', args: ['--no-sandbox', '--use-fake-ui-for-media-stream'] });
    const ctx = b.defaultBrowserContext();
    await ctx.overridePermissions('http://localhost:8080', ['microphone']);
    const pg = await b.newPage();
    const errs = [];
    pg.on('pageerror', e => errs.push(e.message));
    await pg.goto('http://localhost:8080/chat', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise(r => setTimeout(r, 1000));

    // 1. Voice btn visible, send btn hidden (no text)
    const voiceVisible = await pg.$eval('#voiceBtn', el => getComputedStyle(el).display !== 'none');
    const sendHidden = await pg.$eval('#sendBtn', el => getComputedStyle(el).display === 'none');
    console.log('1. Voice btn visible (empty):', voiceVisible);
    console.log('2. Send btn hidden (empty):', sendHidden);

    // 2. Click voice btn → active
    await pg.click('#voiceBtn');
    await new Promise(r => setTimeout(r, 500));
    const voiceActive = await pg.$eval('#voiceBtn', el => el.classList.contains('active'));
    console.log('3. Voice active after click:', voiceActive);

    // 3. Click voice btn again → inactive
    await pg.click('#voiceBtn');
    await new Promise(r => setTimeout(r, 300));
    const voiceOff = await pg.$eval('#voiceBtn', el => !el.classList.contains('active'));
    console.log('4. Voice off after 2nd click:', voiceOff);

    // 4. Type → send visible, voice hidden
    await pg.type('#messageInput', 'hello');
    await new Promise(r => setTimeout(r, 300));
    const sendVis = await pg.$eval('#sendBtn', el => getComputedStyle(el).display !== 'none');
    const voiceHid = await pg.$eval('#voiceBtn', el => getComputedStyle(el).display === 'none');
    console.log('5. Send visible (text):', sendVis);
    console.log('6. Voice hidden (text):', voiceHid);

    // 5. Click send → chat works
    await pg.click('#sendBtn');
    await new Promise(r => setTimeout(r, 6000));
    const msgs = await pg.$$eval('.message', els => els.length);
    console.log('7. Messages:', msgs);

    // 6. After send → voice back
    const voiceBack = await pg.$eval('#voiceBtn', el => getComputedStyle(el).display !== 'none');
    console.log('8. Voice btn back:', voiceBack);

    console.log('\nErrors:', errs.length ? errs.join('; ') : 'None');
    await pg.screenshot({ path: 'ui_test/screenshots/voice_btn_test.png' });
    await b.close();
})();
