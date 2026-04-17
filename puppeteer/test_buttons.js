const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });
    await page.goto('http://localhost:8080/chat', { waitUntil: 'networkidle0', timeout: 15000 });

    const results = [];

    async function testBtn(name, selector, clickIt) {
        try {
            const el = await page.$(selector);
            if (!el) { results.push({ btn: name, ok: false, err: 'NOT FOUND' }); return; }
            if (clickIt) await el.click();
            results.push({ btn: name, ok: true });
        } catch (e) {
            results.push({ btn: name, ok: false, err: e.message.substring(0, 60) });
        }
    }

    // 1-3: Sidebar buttons
    await testBtn('1. New Chat', '#newChatBtn', true);
    await testBtn('2. Search', '#searchBtn', false); // skip click (prompt dialog)
    await testBtn('3. Collapse Sidebar', '#sidebarCollapseBtn', true);
    await new Promise(r => setTimeout(r, 300));
    // Re-show sidebar
    const sidebar = await page.$('#sidebar');
    if (sidebar) await page.evaluate(el => el.style.display = '', sidebar);

    // 4-6: Header buttons
    await testBtn('4. Model Selector', '#modelSelector', true);
    await testBtn('5. Share', '#shareBtn', true);
    await testBtn('6. Settings', '#settingsBtn', false); // don't click (navigates away)

    // 7: User profile
    await testBtn('7. User Profile', '#userProfileBtn', false);

    // 8-10: Input buttons
    await testBtn('8. Attach (+)', '#attachBtn', false); // don't click (file dialog)
    await testBtn('9. Mic', '#micBtn', false); // don't click (permission)
    await testBtn('10. Send', '#sendBtn', false);

    // 11: Send enables when typing
    try {
        await page.type('#messageInput', 'hello test');
        await new Promise(r => setTimeout(r, 300));
        const disabled = await page.$eval('#sendBtn', el => el.disabled);
        results.push({ btn: '11. Send enables on type', ok: !disabled });
    } catch (e) {
        results.push({ btn: '11. Send enables on type', ok: false, err: e.message.substring(0, 60) });
    }

    // 12: Textarea exists (Enter sends)
    await testBtn('12. Textarea (Enter)', '#messageInput', false);

    // Delete btn (if conversations exist)
    const delBtn = await page.$('.delete-btn');
    results.push({ btn: 'Bonus: Delete btn', ok: delBtn ? true : 'No conversations yet' });

    // Screenshot
    await page.screenshot({ path: 'ui_test/screenshots/buttons_test.png' });

    // Print results
    let pass = 0, fail = 0;
    results.forEach(r => {
        const status = r.ok === true ? 'PASS' : 'FAIL';
        if (r.ok === true) pass++; else fail++;
        console.log(`${status} | ${r.btn}${r.err ? ' | ' + r.err : ''}`);
    });
    console.log(`\nTotal: ${pass} PASS, ${fail} FAIL out of ${results.length}`);

    await browser.close();
})();
