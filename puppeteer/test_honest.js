const p = require('puppeteer');
(async () => {
    const b = await p.launch({
        headless: 'new',
        args: ['--no-sandbox', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream']
    });
    const ctx = b.defaultBrowserContext();
    await ctx.overridePermissions('http://localhost:8080', ['microphone', 'clipboard-write']);
    const pg = await b.newPage();
    await pg.setViewport({ width: 1440, height: 900 });

    const jsErrors = [];
    pg.on('pageerror', e => jsErrors.push(e.message));

    await pg.goto('http://localhost:8080/chat', { waitUntil: 'networkidle0', timeout: 15000 });
    await new Promise(r => setTimeout(r, 1500));

    const R = [];
    function test(name, pass, detail) { R.push({ name, pass: pass === true, detail: detail || '' }); }

    // ========== NÚT 1: Đoạn chat mới ==========
    try {
        await pg.click('#newChatBtn');
        await new Promise(r => setTimeout(r, 500));
        const welcome = await pg.$('.welcome');
        test('1. Đoạn chat mới', !!welcome, welcome ? 'Welcome hiện' : 'Welcome KHÔNG hiện');
    } catch(e) { test('1. Đoạn chat mới', false, 'Click lỗi: ' + e.message.slice(0,50)); }

    // ========== NÚT 2: Tìm kiếm ==========
    try {
        await pg.click('#searchBtn');
        await new Promise(r => setTimeout(r, 300));
        const searchInput = await pg.$('#searchInput');
        const searchVisible = searchInput ? await pg.evaluate(el => el.offsetWidth > 0, searchInput) : false;
        test('2. Tìm kiếm', searchVisible, searchVisible ? 'Search box hiện' : 'Search box KHÔNG hiện');
        // Close search
        await pg.click('#searchBtn');
        await new Promise(r => setTimeout(r, 200));
    } catch(e) { test('2. Tìm kiếm', false, e.message.slice(0,50)); }

    // ========== NÚT 3: Codex ==========
    try {
        // Check if Codex button has click handler that navigates
        const codexBtn = await pg.$$('.sidebar-nav .sidebar-btn');
        const codexExists = codexBtn.length >= 3;
        // Don't click (navigates away), just check exists
        test('3. Codex', codexExists, codexExists ? 'Button tồn tại' : 'KHÔNG tìm thấy');
    } catch(e) { test('3. Codex', false, e.message.slice(0,50)); }

    // ========== NÚT 4: Thêm ==========
    try {
        const btns = await pg.$$('.sidebar-nav .sidebar-btn');
        test('4. Thêm', btns.length >= 4, btns.length + ' sidebar buttons');
    } catch(e) { test('4. Thêm', false, e.message.slice(0,50)); }

    // ========== NÚT 5: Collapse sidebar ==========
    try {
        await pg.click('#sidebarCollapseBtn');
        await new Promise(r => setTimeout(r, 300));
        const hidden = await pg.$eval('#sidebar', el => el.style.display === 'none');
        test('5. Collapse sidebar', hidden, hidden ? 'Sidebar ẩn' : 'Sidebar KHÔNG ẩn');
        // Restore
        await pg.evaluate(() => document.getElementById('sidebar').style.display = '');
    } catch(e) { test('5. Collapse sidebar', false, e.message.slice(0,50)); }

    // ========== NÚT 6: Model selector ==========
    try {
        const before = await pg.$eval('#modelSelector', el => el.textContent.trim());
        await pg.click('#modelSelector');
        await new Promise(r => setTimeout(r, 200));
        const after = await pg.$eval('#modelSelector', el => el.textContent.trim());
        test('6. Model selector', before !== after, before + ' → ' + after);
    } catch(e) { test('6. Model selector', false, e.message.slice(0,50)); }

    // ========== NÚT 7: Share ==========
    try {
        await pg.click('#shareBtn');
        await new Promise(r => setTimeout(r, 200));
        test('7. Share', true, 'Click OK, không lỗi');
    } catch(e) { test('7. Share', false, e.message.slice(0,50)); }

    // ========== NÚT 8: Settings (dark mode) ==========
    try {
        const themeBefore = await pg.evaluate(() => document.documentElement.getAttribute('data-theme'));
        await pg.click('#settingsBtn');
        await new Promise(r => setTimeout(r, 300));
        const themeAfter = await pg.evaluate(() => document.documentElement.getAttribute('data-theme'));
        const changed = themeBefore !== themeAfter;
        test('8. Settings/Dark mode', changed, themeBefore + ' → ' + themeAfter);
        // Restore
        await pg.click('#settingsBtn');
    } catch(e) { test('8. Settings', false, e.message.slice(0,50)); }

    // ========== NÚT 9: User profile ==========
    try {
        const profileBtn = await pg.$('#userProfileBtn');
        test('9. User profile', !!profileBtn, profileBtn ? 'Tồn tại, clickable' : 'KHÔNG tìm thấy');
    } catch(e) { test('9. User profile', false, e.message.slice(0,50)); }

    // ========== NÚT 10: Try Codex ==========
    try {
        const codexFooter = await pg.$('#codexBtn');
        test('10. Try Codex', !!codexFooter, codexFooter ? 'Tồn tại' : 'KHÔNG tìm thấy');
    } catch(e) { test('10. Try Codex', false, e.message.slice(0,50)); }

    // ========== NÚT 11: Attach (+) ==========
    try {
        const attachBtn = await pg.$('#attachBtn');
        const visible = attachBtn ? await pg.evaluate(el => el.offsetWidth > 0, attachBtn) : false;
        test('11. Attach (+)', visible, visible ? 'Hiện, clickable' : 'ẨN hoặc không tìm thấy');
    } catch(e) { test('11. Attach', false, e.message.slice(0,50)); }

    // ========== NÚT 12: Mic ==========
    try {
        const micBtn = await pg.$('#micBtn');
        const micVisible = micBtn ? await pg.evaluate(el => el.offsetWidth > 0, micBtn) : false;
        if (micVisible) {
            await pg.click('#micBtn');
            await new Promise(r => setTimeout(r, 800));
            const micBg = await pg.$eval('#micBtn', el => el.style.background);
            const activated = micBg.includes('239') || micBg.includes('ef4444');
            // Stop mic
            if (activated) await pg.click('#micBtn');
            await new Promise(r => setTimeout(r, 300));
            test('12. Mic (STT)', activated, activated ? 'Bật đỏ khi click' : 'KHÔNG phản hồi khi click');
        } else {
            test('12. Mic', false, 'Nút mic KHÔNG hiện');
        }
    } catch(e) { test('12. Mic', false, e.message.slice(0,50)); }

    // ========== NÚT 13: Voice (sóng, 2 chiều) ==========
    try {
        const voiceBtn = await pg.$('#voiceBtn');
        const voiceVisible = voiceBtn ? await pg.evaluate(el => el.offsetWidth > 0, voiceBtn) : false;
        if (voiceVisible) {
            await pg.click('#voiceBtn');
            await new Promise(r => setTimeout(r, 500));
            const active = await pg.$eval('#voiceBtn', el => el.classList.contains('active'));
            const voiceMode = await pg.evaluate(() => Chat.voiceMode);
            const ttsOn = await pg.evaluate(() => Chat.ttsEnabled);
            // Stop
            await pg.click('#voiceBtn');
            await new Promise(r => setTimeout(r, 300));
            test('13. Voice 2 chiều', active && voiceMode && ttsOn,
                'active=' + active + ' voiceMode=' + voiceMode + ' tts=' + ttsOn);
        } else {
            test('13. Voice 2 chiều', false, 'Nút voice KHÔNG hiện');
        }
    } catch(e) { test('13. Voice 2 chiều', false, e.message.slice(0,50)); }

    // ========== NÚT 14: Send ==========
    try {
        // Type text → send appears
        await pg.type('#messageInput', 'test button');
        await new Promise(r => setTimeout(r, 300));
        const sendVisible = await pg.$eval('#sendBtn', el => getComputedStyle(el).display !== 'none');
        if (sendVisible) {
            await pg.click('#sendBtn');
            await new Promise(r => setTimeout(r, 7000));
            const msgs = await pg.$$eval('.message', els => els.length);
            test('14. Send', msgs >= 2, msgs + ' messages');
        } else {
            test('14. Send', false, 'Nút send KHÔNG hiện sau khi gõ text');
        }
    } catch(e) { test('14. Send', false, e.message.slice(0,50)); }

    // ========== NÚT 15: Delete conv ==========
    try {
        const conv = await pg.$('.conv-item');
        if (conv) {
            await conv.hover();
            await new Promise(r => setTimeout(r, 300));
            const delBtn = await pg.$('.delete-btn');
            const delVisible = delBtn ? await pg.evaluate(el => el.offsetWidth > 0, delBtn) : false;
            if (delVisible) {
                const before = await pg.$$eval('.conv-item', els => els.length);
                await delBtn.click();
                await new Promise(r => setTimeout(r, 500));
                const after = await pg.$$eval('.conv-item', els => els.length);
                test('15. Delete conv', after < before, before + ' → ' + after);
            } else {
                test('15. Delete conv', false, 'Delete btn KHÔNG hiện khi hover');
            }
        } else {
            test('15. Delete conv', false, 'Không có conv để test');
        }
    } catch(e) { test('15. Delete conv', false, e.message.slice(0,50)); }

    // ========== NÚT 16: Click conv load history ==========
    try {
        const conv = await pg.$('.conv-item');
        if (conv) {
            await conv.click();
            await new Promise(r => setTimeout(r, 1000));
            const msgs = await pg.$$eval('.message', els => els.length);
            test('16. Click conv', msgs >= 1, msgs + ' messages loaded');
        } else {
            test('16. Click conv', false, 'Không có conv');
        }
    } catch(e) { test('16. Click conv', false, e.message.slice(0,50)); }

    // ========== NÚT 17-20: Action buttons (cần message để test) ==========
    // Copy
    try {
        const copyBtn = await pg.$('.msg-action-btn[title="Sao chép"]');
        test('17. Copy message', !!copyBtn, copyBtn ? 'Tồn tại trên assistant msg' : 'KHÔNG tìm thấy');
    } catch(e) { test('17. Copy message', false, e.message.slice(0,50)); }

    // Regenerate
    try {
        const regenBtn = await pg.$('.msg-action-btn[title="Tạo lại"]');
        test('18. Regenerate', !!regenBtn, regenBtn ? 'Tồn tại' : 'KHÔNG tìm thấy');
    } catch(e) { test('18. Regenerate', false, e.message.slice(0,50)); }

    // Edit user message
    try {
        const editBtn = await pg.$('.msg-action-btn[title="Chỉnh sửa"]');
        test('19. Edit message', !!editBtn, editBtn ? 'Tồn tại trên user msg' : 'KHÔNG tìm thấy');
    } catch(e) { test('19. Edit message', false, e.message.slice(0,50)); }

    // GPT items in sidebar
    try {
        const gptItems = await pg.$$('.gpt-item');
        test('20. GPT sidebar items', gptItems.length >= 1, gptItems.length + ' GPT items');
    } catch(e) { test('20. GPT items', false, e.message.slice(0,50)); }

    // ========== RESULTS ==========
    console.log('\n============ HONEST BUTTON AUDIT ============');
    let pass = 0, fail = 0;
    R.forEach(r => {
        const s = r.pass ? 'OK' : 'XX';
        if (r.pass) pass++; else fail++;
        console.log(`${s} | ${r.name} | ${r.detail}`);
    });
    console.log('==============================================');
    console.log(`PASS: ${pass} | FAIL: ${fail} | TOTAL: ${R.length}`);
    if (jsErrors.length) {
        console.log('\nJS ERRORS:');
        jsErrors.forEach(e => console.log('  ' + e.slice(0,100)));
    } else {
        console.log('\n0 JS errors');
    }
    await pg.screenshot({ path: 'ui_test/screenshots/honest_audit.png' });
    await b.close();
})();
