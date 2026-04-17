const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });

    const errors = [];
    page.on('pageerror', err => errors.push('JS: ' + err.message));
    page.on('console', msg => { if (msg.type() === 'error' && !msg.text().includes('favicon')) errors.push('Console: ' + msg.text()); });

    console.log('1. Loading page...');
    await page.goto('http://localhost:8080/chat', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise(r => setTimeout(r, 1000));

    console.log('2. Checking JS loaded...');
    const jsOk = await page.evaluate(() => typeof Chat !== 'undefined' && typeof Sidebar !== 'undefined');
    console.log('   Chat+Sidebar:', jsOk ? 'OK' : 'FAIL');

    console.log('3. Typing message...');
    await page.click('#messageInput');
    await page.type('#messageInput', 'Hello xin chao');
    await new Promise(r => setTimeout(r, 300));
    const val = await page.$eval('#messageInput', el => el.value);
    console.log('   Input value:', val);
    const btnEnabled = await page.$eval('#sendBtn', el => !el.disabled);
    console.log('   Send enabled:', btnEnabled);

    console.log('4. Clicking send...');
    await page.click('#sendBtn');

    console.log('5. Waiting 8s for streaming...');
    await new Promise(r => setTimeout(r, 8000));

    const msgs = await page.$$eval('.message', els => els.map(el => ({
        role: el.classList.contains('user') ? 'user' : 'assistant',
        text: el.querySelector('.message-content')?.textContent?.substring(0, 80) || 'EMPTY'
    })));
    console.log('6. Messages:', JSON.stringify(msgs, null, 2));

    const convs = await page.$$eval('.conv-item', els => els.map(el => el.textContent.trim()));
    console.log('7. Sidebar convs:', convs);

    if (errors.length) {
        console.log('\nERRORS:');
        errors.forEach(e => console.log('  ', e));
    } else {
        console.log('\nNo JS errors');
    }

    await page.screenshot({ path: 'ui_test/screenshots/chat_flow_test.png' });
    console.log('Screenshot saved');
    await browser.close();
})();
