const p = require('puppeteer');
(async () => {
    const b = await p.launch({ headless: 'new', args: ['--no-sandbox'] });
    const pg = await b.newPage();
    await pg.setViewport({ width: 1440, height: 900 });
    const errs = [];
    pg.on('pageerror', e => errs.push(e.message));
    await pg.goto('http://localhost:8080/chat', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise(r => setTimeout(r, 1500));

    // Check 6 mode buttons
    const modes = await pg.$$eval('.mode-btn', els => els.map(e => ({
        mode: e.dataset.mode,
        text: e.textContent.trim(),
        visible: e.offsetWidth > 0
    })));
    console.log('=== MODE BUTTONS ===');
    modes.forEach(m => console.log(`${m.visible ? 'OK' : 'XX'} | ${m.mode} | ${m.text}`));

    // Click Ask
    await pg.click('[data-mode="ask"]');
    await new Promise(r => setTimeout(r, 300));
    const askActive = await pg.$eval('[data-mode="ask"]', el => el.classList.contains('active'));
    const ph = await pg.$eval('#messageInput', el => el.placeholder);
    console.log('\n=== ASK MODE ===');
    console.log('Active:', askActive);
    console.log('Placeholder:', ph);

    // Click Plan
    await pg.click('[data-mode="plan"]');
    await new Promise(r => setTimeout(r, 200));
    const planActive = await pg.$eval('[data-mode="plan"]', el => el.classList.contains('active'));
    const askOff = await pg.$eval('[data-mode="ask"]', el => !el.classList.contains('active'));
    console.log('\n=== PLAN MODE ===');
    console.log('Plan active:', planActive);
    console.log('Ask deactivated:', askOff);

    // Toggle off
    await pg.click('[data-mode="plan"]');
    await new Promise(r => setTimeout(r, 200));
    const allOff = await pg.$$eval('.mode-btn', els => els.every(e => !e.classList.contains('active')));
    console.log('All off after toggle:', allOff);

    console.log('\nErrors:', errs.length ? errs.join('; ') : 'None');
    await pg.screenshot({ path: 'ui_test/screenshots/modes_ui.png' });
    await b.close();
})();
