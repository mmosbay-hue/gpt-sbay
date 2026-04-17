const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream']
    });
    const ctx = browser.defaultBrowserContext();
    await ctx.overridePermissions('http://localhost:8080', ['microphone', 'clipboard-write']);

    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });

    const jsErrors = [];
    page.on('pageerror', e => jsErrors.push(e.message));
    page.on('console', m => { if (m.type() === 'error' && !m.text().includes('favicon')) jsErrors.push(m.text()); });

    await page.goto('http://localhost:8080/chat', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise(r => setTimeout(r, 1500));

    const R = []; // results
    function log(name, pass, detail) { R.push({ name, pass, detail }); }

    // ========== 1. PAGE LOAD ==========
    const title = await page.title();
    log('1. Page title', title === 'ChatGPT', title);

    const welcome = await page.$eval('.welcome h1', el => el.textContent).catch(() => '');
    log('2. Welcome text', welcome.includes('sẵn sàng'), welcome.substring(0, 50));

    // ========== 2. SIDEBAR STRUCTURE ==========
    const logoExists = await page.$('.sidebar-logo svg') !== null;
    log('3. OpenAI logo', logoExists, '');

    const collapseBtn = await page.$('#sidebarCollapseBtn') !== null;
    log('4. Collapse btn', collapseBtn, '');

    const navBtns = await page.$$eval('.sidebar-nav .sidebar-btn', els => els.map(e => e.textContent.trim()));
    log('5. Nav: Đoạn chat mới', navBtns.some(t => t.includes('chat mới')), navBtns.join(' | '));
    log('6. Nav: Tìm kiếm', navBtns.some(t => t.includes('Tìm kiếm')), '');
    log('7. Nav: Codex', navBtns.some(t => t.includes('Codex')), '');
    log('8. Nav: Thêm', navBtns.some(t => t.includes('Thêm')), '');

    const gptSection = await page.$('.sidebar-section-title');
    const gptLabel = gptSection ? await page.evaluate(el => el.textContent, gptSection) : '';
    log('9. GPT section label', gptLabel.includes('GPT'), gptLabel);

    const gptItems = await page.$$('.gpt-item');
    log('10. GPT list items', gptItems.length >= 1, `${gptItems.length} items`);

    const userName = await page.$eval('.user-name', el => el.textContent).catch(() => '');
    log('11. User name', userName.length > 0, userName);

    const userPlan = await page.$eval('.user-plan', el => el.textContent).catch(() => '');
    log('12. User plan text', userPlan.includes('Tài khoản'), userPlan);

    const codexBtn = await page.$('.codex-btn');
    log('13. Try Codex btn', codexBtn !== null, '');

    // ========== 3. HEADER ==========
    const modelText = await page.$eval('#modelSelector', el => el.textContent.trim()).catch(() => '');
    log('14. Model selector', modelText.includes('ChatGPT'), modelText);

    const shareBtn = await page.$('#shareBtn') !== null;
    log('15. Share btn', shareBtn, '');

    const settingsBtn = await page.$('#settingsBtn') !== null;
    log('16. Settings btn', settingsBtn, '');

    // ========== 4. INPUT BOX ==========
    const attachBtn = await page.$('#attachBtn') !== null;
    log('17. Attach (+) btn', attachBtn, '');

    const placeholder = await page.$eval('#messageInput', el => el.placeholder).catch(() => '');
    log('18. Placeholder text', placeholder.includes('Hỏi bất kỳ'), placeholder);

    const micBtn = await page.$('#micBtn') !== null;
    log('19. Mic btn', micBtn, '');

    const sendBtn = await page.$('#sendBtn') !== null;
    log('20. Send btn', sendBtn, '');

    // Send btn disabled when empty
    const sendDisabled = await page.$eval('#sendBtn', el => el.disabled);
    log('21. Send disabled when empty', sendDisabled, '');

    // Audio icon visible when disabled
    const audioIcon = await page.$eval('#sendBtn .icon-audio', el => getComputedStyle(el).display !== 'none').catch(() => false);
    log('22. Audio wave icon (disabled)', audioIcon, '');

    // ========== 5. FUNCTIONAL TESTS ==========

    // 5a. Collapse sidebar
    await page.click('#sidebarCollapseBtn');
    await new Promise(r => setTimeout(r, 300));
    const sidebarHidden = await page.$eval('#sidebar', el => el.style.display === 'none');
    log('23. Collapse hides sidebar', sidebarHidden, '');
    await page.evaluate(() => document.getElementById('sidebar').style.display = '');

    // 5b. Type + send enables
    await page.type('#messageInput', 'hello');
    await new Promise(r => setTimeout(r, 300));
    const sendEnabled = !(await page.$eval('#sendBtn', el => el.disabled));
    log('24. Send enables on type', sendEnabled, '');

    // Send icon swaps to arrow
    const sendIconVisible = await page.$eval('#sendBtn .icon-send', el => getComputedStyle(el).display !== 'none').catch(() => false);
    log('25. Arrow icon on enabled', sendIconVisible, '');

    // 5c. Send message
    await page.click('#sendBtn');
    await new Promise(r => setTimeout(r, 8000));
    const msgCount = await page.$$eval('.message', els => els.length);
    log('26. Messages after send', msgCount >= 2, `${msgCount} messages`);

    // Check user message has avatar + role
    const userAvatar = await page.$('.message.user .message-avatar') !== null;
    log('27. User avatar', userAvatar, '');
    const userRole = await page.$eval('.message.user .message-role', el => el.textContent).catch(() => '');
    log('28. User role "You"', userRole === 'You', userRole);

    // Check assistant message
    const assistAvatar = await page.$('.message.assistant .message-avatar') !== null;
    log('29. Assistant avatar', assistAvatar, '');
    const assistRole = await page.$eval('.message.assistant .message-role', el => el.textContent).catch(() => '');
    log('30. Assistant role', assistRole === 'GPT Web', assistRole);

    const assistContent = await page.$eval('.message.assistant .message-content', el => el.textContent.substring(0, 60)).catch(() => '');
    log('31. Assistant replied', assistContent.length > 5, assistContent);

    // 5d. Sidebar conversation appeared
    const convs = await page.$$('.conv-item');
    log('32. Conv in sidebar', convs.length >= 1, `${convs.length}`);

    // 5e. New chat clears
    await page.click('#newChatBtn');
    await new Promise(r => setTimeout(r, 500));
    const welcomeBack = await page.$('.welcome') !== null;
    log('33. New chat shows welcome', welcomeBack, '');

    // 5f. Click conv loads history
    const conv = await page.$('.conv-item');
    if (conv) {
        await conv.click();
        await new Promise(r => setTimeout(r, 1000));
        const loaded = await page.$$eval('.message', els => els.length);
        log('34. Load history', loaded >= 2, `${loaded} msgs`);
    } else {
        log('34. Load history', false, 'no conv');
    }

    // 5g. Delete conv
    const convDel = await page.$('.conv-item');
    if (convDel) {
        await convDel.hover();
        await new Promise(r => setTimeout(r, 300));
        const del = await page.$('.delete-btn');
        if (del) {
            const before = await page.$$eval('.conv-item', els => els.length);
            await del.click();
            await new Promise(r => setTimeout(r, 500));
            const after = await page.$$eval('.conv-item', els => els.length);
            log('35. Delete conv', after < before, `${before} -> ${after}`);
        } else {
            log('35. Delete conv', false, 'delete btn not visible');
        }
    } else {
        log('35. Delete conv', false, 'no conv');
    }

    // 5h. Model selector cycles
    const mBefore = await page.$eval('#modelSelector', el => el.textContent.trim());
    await page.click('#modelSelector');
    await new Promise(r => setTimeout(r, 200));
    const mAfter = await page.$eval('#modelSelector', el => el.textContent.trim());
    log('36. Model selector cycles', mBefore !== mAfter, `${mBefore} -> ${mAfter}`);

    // 5i. Mic activates
    await page.click('#micBtn');
    await new Promise(r => setTimeout(r, 1000));
    const micBg = await page.$eval('#micBtn', el => el.style.background);
    log('37. Mic activates (red bg)', micBg.includes('239') || micBg.includes('ef4444'), micBg);
    await page.click('#micBtn'); // stop

    // ========== RESULTS ==========
    await page.screenshot({ path: 'ui_test/screenshots/full_audit.png' });

    console.log('\n============ FULL UI/UX AUDIT ============');
    let pass = 0, fail = 0;
    R.forEach(r => {
        const s = r.pass ? 'OK' : 'XX';
        if (r.pass) pass++; else fail++;
        console.log(`${s} | ${r.name}${r.detail ? ' | ' + r.detail : ''}`);
    });
    console.log('==========================================');
    console.log(`PASS: ${pass} | FAIL: ${fail} | TOTAL: ${R.length}`);

    if (jsErrors.length) {
        console.log('\nJS ERRORS:');
        jsErrors.forEach(e => console.log('  ' + e.substring(0, 100)));
    } else {
        console.log('\n0 JS errors');
    }

    await browser.close();
})();
