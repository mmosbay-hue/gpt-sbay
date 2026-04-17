const p = require('puppeteer');
(async () => {
    const b = await p.launch({
        headless: false, // VISIBLE browser để xem thật
        args: ['--no-sandbox', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--auto-accept-camera-and-microphone-capture']
    });
    const ctx = b.defaultBrowserContext();
    await ctx.overridePermissions('http://localhost:8080', ['microphone']);
    const pg = await b.newPage();
    await pg.setViewport({ width: 1440, height: 900 });

    // Capture ALL console messages
    pg.on('console', m => console.log(`[${m.type()}] ${m.text()}`));
    pg.on('pageerror', e => console.log('[PAGE ERROR]', e.message));

    await pg.goto('http://localhost:8080/chat', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise(r => setTimeout(r, 2000));

    // Screenshot before click
    await pg.screenshot({ path: 'ui_test/screenshots/debug_before_click.png' });
    console.log('\n=== SCREENSHOT TAKEN (before click) ===');

    // Check what elements exist in input area
    const inputArea = await pg.evaluate(() => {
        const wrapper = document.querySelector('.input-wrapper');
        if (!wrapper) return 'INPUT WRAPPER NOT FOUND';
        const children = Array.from(wrapper.querySelectorAll('*')).map(el => ({
            tag: el.tagName,
            id: el.id,
            class: el.className,
            display: getComputedStyle(el).display,
            disabled: el.disabled,
            visible: el.offsetWidth > 0
        }));
        return children;
    });
    console.log('\n=== INPUT AREA ELEMENTS ===');
    console.log(JSON.stringify(inputArea, null, 2));

    // Check voice btn specifically
    const voiceBtnInfo = await pg.evaluate(() => {
        const btn = document.getElementById('voiceBtn');
        if (!btn) return 'voiceBtn NOT FOUND';
        return {
            id: btn.id,
            display: getComputedStyle(btn).display,
            visible: btn.offsetWidth > 0,
            disabled: btn.disabled,
            className: btn.className,
            innerHTML: btn.innerHTML.substring(0, 50),
            parentId: btn.parentElement?.id,
            parentClass: btn.parentElement?.className
        };
    });
    console.log('\n=== VOICE BTN ===');
    console.log(JSON.stringify(voiceBtnInfo, null, 2));

    // Check send btn
    const sendBtnInfo = await pg.evaluate(() => {
        const btn = document.getElementById('sendBtn');
        if (!btn) return 'sendBtn NOT FOUND';
        return {
            id: btn.id,
            display: getComputedStyle(btn).display,
            visible: btn.offsetWidth > 0,
            disabled: btn.disabled,
        };
    });
    console.log('\n=== SEND BTN ===');
    console.log(JSON.stringify(sendBtnInfo, null, 2));

    // Check mic btn
    const micBtnInfo = await pg.evaluate(() => {
        const btn = document.getElementById('micBtn');
        if (!btn) return 'micBtn NOT FOUND';
        return {
            id: btn.id,
            display: getComputedStyle(btn).display,
            visible: btn.offsetWidth > 0,
        };
    });
    console.log('\n=== MIC BTN ===');
    console.log(JSON.stringify(micBtnInfo, null, 2));

    // Try clicking voice btn
    console.log('\n=== CLICKING VOICE BTN ===');
    try {
        await pg.click('#voiceBtn');
        console.log('Click success');
        await new Promise(r => setTimeout(r, 1500));

        const afterClick = await pg.evaluate(() => {
            const btn = document.getElementById('voiceBtn');
            return {
                className: btn?.className,
                bg: btn?.style.background,
                voiceMode: typeof Chat !== 'undefined' ? Chat.voiceMode : 'Chat not found',
                ttsEnabled: typeof Chat !== 'undefined' ? Chat.ttsEnabled : 'Chat not found'
            };
        });
        console.log('After click:', JSON.stringify(afterClick));
    } catch (e) {
        console.log('Click FAILED:', e.message);
    }

    // Screenshot after click
    await pg.screenshot({ path: 'ui_test/screenshots/debug_after_click.png' });
    console.log('=== SCREENSHOT TAKEN (after click) ===');

    await new Promise(r => setTimeout(r, 3000)); // Keep browser open briefly
    await b.close();
})();
