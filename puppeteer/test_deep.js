const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });

    const jsErrors = [];
    page.on('pageerror', err => jsErrors.push(err.message));
    page.on('console', msg => { if (msg.type() === 'error') jsErrors.push(msg.text()); });

    await page.goto('http://localhost:8080/chat', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise(r => setTimeout(r, 1000));

    console.log('=== JS ERRORS ON LOAD ===');
    jsErrors.forEach(e => console.log('  ' + e));
    if (!jsErrors.length) console.log('  None');

    // Check if app.js loaded properly
    const appLoaded = await page.evaluate(() => typeof Chat !== 'undefined' && typeof Sidebar !== 'undefined' && typeof MD !== 'undefined');
    console.log('\n=== JS MODULES ===');
    console.log('Chat object:', appLoaded ? 'loaded' : 'NOT LOADED');

    // 1. Welcome screen visible?
    console.log('\n=== 1. WELCOME SCREEN ===');
    const welcomeVisible = await page.$eval('.welcome', el => el.offsetHeight > 0).catch(() => false);
    console.log('Welcome visible:', welcomeVisible);

    // 2. Textarea focus?
    console.log('\n=== 2. TEXTAREA ===');
    const focused = await page.evaluate(() => document.activeElement.id);
    console.log('Active element:', focused);

    // 3. Type text -> send btn enables?
    console.log('\n=== 3. TYPE + SEND BTN ===');
    await page.type('#messageInput', 'test 123');
    await new Promise(r => setTimeout(r, 300));
    const sendEnabled = await page.$eval('#sendBtn', el => !el.disabled);
    console.log('Send enabled after type:', sendEnabled);
    const inputVal = await page.$eval('#messageInput', el => el.value);
    console.log('Input value:', inputVal);

    // 4. Click send -> message appears?
    console.log('\n=== 4. SEND MESSAGE ===');
    await page.click('#sendBtn');
    console.log('Clicked send...');
    await new Promise(r => setTimeout(r, 8000)); // wait for streaming

    const msgCount = await page.$$eval('.message', els => els.length);
    console.log('Messages on screen:', msgCount);

    // Check if assistant replied
    const lastMsg = await page.$$eval('.message-content', els => {
        const last = els[els.length - 1];
        return last ? last.textContent.substring(0, 100) : 'NONE';
    });
    console.log('Last message content:', lastMsg);

    // 5. Sidebar has conversation?
    console.log('\n=== 5. SIDEBAR ===');
    const convCount = await page.$$eval('.conv-item', els => els.length);
    console.log('Conversations in sidebar:', convCount);

    // 6. Click New Chat
    console.log('\n=== 6. NEW CHAT ===');
    await page.click('#newChatBtn');
    await new Promise(r => setTimeout(r, 500));
    const welcomeAfter = await page.$('.welcome');
    const msgsAfter = await page.$$eval('.message', els => els.length);
    console.log('Welcome shown after new chat:', !!welcomeAfter);
    console.log('Messages cleared:', msgsAfter === 0);

    // 7. Click conversation to load history
    console.log('\n=== 7. LOAD HISTORY ===');
    const convItem = await page.$('.conv-item');
    if (convItem) {
        await convItem.click();
        await new Promise(r => setTimeout(r, 1000));
        const loaded = await page.$$eval('.message', els => els.length);
        console.log('Messages loaded from history:', loaded);
    } else {
        console.log('No conv to click');
    }

    // 8. Collapse sidebar
    console.log('\n=== 8. COLLAPSE SIDEBAR ===');
    await page.click('#sidebarCollapseBtn');
    await new Promise(r => setTimeout(r, 300));
    const sidebarHidden = await page.$eval('#sidebar', el => el.style.display === 'none' || el.offsetWidth === 0);
    console.log('Sidebar hidden:', sidebarHidden);
    // Re-show
    await page.evaluate(() => document.getElementById('sidebar').style.display = '');

    // 9. Model selector changes
    console.log('\n=== 9. MODEL SELECTOR ===');
    const modelBefore = await page.$eval('#modelSelector', el => el.textContent.trim());
    await page.click('#modelSelector');
    await new Promise(r => setTimeout(r, 200));
    const modelAfter = await page.$eval('#modelSelector', el => el.textContent.trim());
    console.log('Before:', modelBefore, '-> After:', modelAfter, '| Changed:', modelBefore !== modelAfter);

    // 10. Delete conversation
    console.log('\n=== 10. DELETE CONV ===');
    const conv2 = await page.$('.conv-item');
    if (conv2) {
        await conv2.hover();
        await new Promise(r => setTimeout(r, 300));
        const delBtn = await page.$('.delete-btn');
        const delVisible = delBtn ? await page.evaluate(el => el.offsetWidth > 0, delBtn) : false;
        console.log('Delete btn visible on hover:', delVisible);
        if (delBtn && delVisible) {
            const beforeDel = await page.$$eval('.conv-item', els => els.length);
            await delBtn.click();
            await new Promise(r => setTimeout(r, 500));
            const afterDel = await page.$$eval('.conv-item', els => els.length);
            console.log('Before delete:', beforeDel, '-> After:', afterDel);
        }
    } else {
        console.log('No conv to delete');
    }

    // 11. Attach btn clickable (opens file dialog)
    console.log('\n=== 11. ATTACH BTN ===');
    const attachBtn = await page.$('#attachBtn');
    console.log('Attach btn exists:', !!attachBtn);

    // 12. Mic btn clickable
    console.log('\n=== 12. MIC BTN ===');
    const micBtn = await page.$('#micBtn');
    console.log('Mic btn exists:', !!micBtn);

    // Final errors
    console.log('\n=== FINAL JS ERRORS ===');
    const finalErrors = jsErrors.filter(e => !e.includes('favicon'));
    finalErrors.forEach(e => console.log('  ' + e));
    if (!finalErrors.length) console.log('  None');

    await page.screenshot({ path: 'ui_test/screenshots/deep_test.png' });
    console.log('\nScreenshot: ui_test/screenshots/deep_test.png');
    await browser.close();
})();
