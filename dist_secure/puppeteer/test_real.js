const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
    const page = await browser.newPage();

    // Catch console errors
    const errors = [];
    page.on('console', msg => {
        if (msg.type() === 'error') errors.push(msg.text());
    });
    page.on('pageerror', err => errors.push('PAGE ERROR: ' + err.message));

    await page.setViewport({ width: 1440, height: 900 });
    await page.goto('http://localhost:8080/chat', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise(r => setTimeout(r, 1000));

    // Print all console errors
    console.log('=== JS ERRORS ===');
    if (errors.length === 0) console.log('None');
    else errors.forEach(e => console.log('ERROR:', e));

    // Test: type and send a message
    console.log('\n=== SEND MESSAGE TEST ===');
    try {
        await page.type('#messageInput', 'hello');
        await new Promise(r => setTimeout(r, 300));

        const sendDisabled = await page.$eval('#sendBtn', el => el.disabled);
        console.log('Send btn disabled after typing:', sendDisabled);

        await page.click('#sendBtn');
        console.log('Clicked send');

        await new Promise(r => setTimeout(r, 5000));

        const messages = await page.$$('.message');
        console.log('Messages on screen:', messages.length);

        const convItems = await page.$$('.conv-item');
        console.log('Conversations in sidebar:', convItems.length);
    } catch (e) {
        console.log('SEND ERROR:', e.message);
    }

    // Check all errors after interaction
    console.log('\n=== ERRORS AFTER INTERACTION ===');
    if (errors.length === 0) console.log('None');
    else errors.forEach(e => console.log('ERROR:', e));

    await page.screenshot({ path: 'ui_test/screenshots/real_test.png' });
    console.log('\nScreenshot saved');

    await browser.close();
})();
