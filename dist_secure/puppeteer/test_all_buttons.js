const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });

    const errors = [];
    page.on('pageerror', err => errors.push(err.message));

    await page.goto('http://localhost:8080/chat', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise(r => setTimeout(r, 500));

    const results = [];

    // === 1. New Chat ===
    try {
        await page.click('#newChatBtn');
        const welcome = await page.$('.welcome');
        results.push(['1. New Chat', welcome ? 'PASS' : 'FAIL - welcome not shown']);
    } catch(e) { results.push(['1. New Chat', 'FAIL - ' + e.message.slice(0,50)]); }

    // === 2. Type + Send + Streaming ===
    try {
        await page.type('#messageInput', 'say hi');
        await new Promise(r => setTimeout(r, 200));
        const enabled = !(await page.$eval('#sendBtn', el => el.disabled));
        if (!enabled) { results.push(['2. Send btn enable', 'FAIL - still disabled']); }
        else { results.push(['2. Send btn enable', 'PASS']); }

        await page.click('#sendBtn');
        await new Promise(r => setTimeout(r, 6000)); // wait streaming

        const msgs = await page.$$('.message');
        results.push(['3. Messages appear', msgs.length >= 2 ? 'PASS (' + msgs.length + ' messages)' : 'FAIL (' + msgs.length + ')']);

        const convs = await page.$$('.conv-item');
        results.push(['4. Sidebar conv appears', convs.length >= 1 ? 'PASS (' + convs.length + ')' : 'FAIL']);
    } catch(e) { results.push(['2-4. Chat flow', 'FAIL - ' + e.message.slice(0,80)]); }

    // === 5. Collapse sidebar ===
    try {
        await page.click('#sidebarCollapseBtn');
        await new Promise(r => setTimeout(r, 300));
        const hidden = await page.$eval('#sidebar', el => el.style.display === 'none');
        results.push(['5. Collapse sidebar', hidden ? 'PASS' : 'FAIL - not hidden']);
        // Re-show
        await page.evaluate(() => document.getElementById('sidebar').style.display = '');
    } catch(e) { results.push(['5. Collapse sidebar', 'FAIL - ' + e.message.slice(0,50)]); }

    // === 6. Model selector ===
    try {
        const before = await page.$eval('#modelSelector', el => el.textContent.trim());
        await page.click('#modelSelector');
        await new Promise(r => setTimeout(r, 200));
        const after = await page.$eval('#modelSelector', el => el.textContent.trim());
        results.push(['6. Model selector', before !== after ? 'PASS (' + after + ')' : 'FAIL - did not change']);
    } catch(e) { results.push(['6. Model selector', 'FAIL - ' + e.message.slice(0,50)]); }

    // === 7. Click conversation (load history) ===
    try {
        const conv = await page.$('.conv-item');
        if (conv) {
            await conv.click();
            await new Promise(r => setTimeout(r, 1000));
            const msgs = await page.$$('.message');
            results.push(['7. Click conv loads history', msgs.length >= 2 ? 'PASS' : 'FAIL']);
        } else {
            results.push(['7. Click conv', 'SKIP - no conversations']);
        }
    } catch(e) { results.push(['7. Click conv', 'FAIL - ' + e.message.slice(0,50)]); }

    // === 8. Delete conversation ===
    try {
        const conv = await page.$('.conv-item');
        if (conv) {
            await conv.hover();
            await new Promise(r => setTimeout(r, 200));
            const delBtn = await page.$('.delete-btn');
            if (delBtn) {
                await delBtn.click();
                await new Promise(r => setTimeout(r, 500));
                const remaining = await page.$$('.conv-item');
                results.push(['8. Delete conv', 'PASS (remaining: ' + remaining.length + ')']);
            } else {
                results.push(['8. Delete conv', 'FAIL - delete btn not visible on hover']);
            }
        } else {
            results.push(['8. Delete conv', 'SKIP - no conversations']);
        }
    } catch(e) { results.push(['8. Delete conv', 'FAIL - ' + e.message.slice(0,50)]); }

    // === 9. Attach btn exists ===
    try {
        const btn = await page.$('#attachBtn');
        results.push(['9. Attach (+)', btn ? 'PASS - exists' : 'FAIL - not found']);
    } catch(e) { results.push(['9. Attach', 'FAIL']); }

    // === 10. Mic btn exists ===
    try {
        const btn = await page.$('#micBtn');
        results.push(['10. Mic', btn ? 'PASS - exists' : 'FAIL - not found']);
    } catch(e) { results.push(['10. Mic', 'FAIL']); }

    // === 11. Share ===
    try {
        await page.click('#shareBtn');
        results.push(['11. Share', 'PASS - clicked']);
    } catch(e) { results.push(['11. Share', 'FAIL']); }

    // === 12. Settings exists ===
    try {
        const btn = await page.$('#settingsBtn');
        results.push(['12. Settings', btn ? 'PASS - exists' : 'FAIL']);
    } catch(e) { results.push(['12. Settings', 'FAIL']); }

    // Print
    console.log('\n========== BUTTON TEST RESULTS ==========');
    let pass = 0, fail = 0;
    results.forEach(([name, status]) => {
        const ok = status.startsWith('PASS');
        if (ok) pass++; else fail++;
        console.log((ok ? 'OK' : 'XX') + ' | ' + name + ' | ' + status);
    });
    console.log('=========================================');
    console.log('PASS: ' + pass + ' | FAIL: ' + fail + ' | TOTAL: ' + results.length);

    if (errors.length) {
        console.log('\nJS ERRORS:');
        errors.forEach(e => console.log('  ' + e.slice(0, 100)));
    }

    await page.screenshot({ path: 'ui_test/screenshots/all_buttons.png' });
    await browser.close();
})();
