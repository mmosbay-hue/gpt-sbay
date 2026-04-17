/**
 * Audit moi nut tren /chat — reload sach trang truoc moi test, capture nav qua page.on('request').
 */
const puppeteer = require('puppeteer');

const STAY_BUTTONS = [
    { id: 'sidebarCollapseBtn', name: 'Sidebar Collapse', test: 'classToggle', selector: '#sidebar', expectClass: 'collapsed' },
    { id: 'newChatBtn', name: 'New Chat', test: 'newChat' },
    { id: 'searchBtn', name: 'Search', test: 'showSearchBox' },
    { id: 'shareBtn', name: 'Share', test: 'shareCopy' },
    { id: 'settingsBtn', name: 'Settings (Dark mode)', test: 'darkToggle' },
    { id: 'sidebarToggle', name: 'Mobile Toggle', test: 'classToggle', selector: '#sidebar', expectClass: 'open', viewport: { width: 600, height: 800 } },
    { id: 'attachBtn', name: 'Attach File', test: 'attachExists' },
    { id: 'micBtn', name: 'Mic', test: 'micToggle' },
    { id: 'voiceBtn', name: 'Voice Mode', test: 'voiceModeToggle' },
    { id: 'sendBtn', name: 'Send (empty)', test: 'sendEmpty' },
    { id: 'modelSelector', name: 'Model Selector', test: 'modelChange' },
];

const NAVIGATE_BUTTONS = [
    { id: 'codexBtn', name: 'Try Codex Footer', expectUrl: '/gpt-builder' },
    { id: 'userProfileBtn', name: 'User Profile', expectUrl: '/dashboard' },
];

const NAVIGATE_NAV_BUTTONS = [
    { idx: 2, name: 'Codex (nav)', expectUrl: '/gpt-builder' },
    { idx: 3, name: 'Thêm (nav)', expectUrl: '/dashboard' },
];

const GPT_ITEMS = [
    { idx: 0, name: 'GPT TRỢ LÝ VIẾT SÁCH' },
    { idx: 1, name: 'GPT BNI CONNECT' },
    { idx: 2, name: 'GPT AI AGENT' },
    { idx: 3, name: 'GPT SỨC KHỎE' },
];

async function loadPage(page, viewport = { width: 1366, height: 800 }) {
    await page.setViewport(viewport);
    await page.goto('http://localhost:8080/chat', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await new Promise(r => setTimeout(r, 600));
}

async function captureNavigation(page, clickFn) {
    // Patch location.assign + location.replace + form submission + anchor click
    // For inline `window.location.href = ...` we use Proxy on a wrapper.
    let captured = null;
    const onReq = (req) => {
        if (req.isNavigationRequest() && req.frame() === page.mainFrame() && req.url() !== page.url()) {
            captured = req.url();
        }
    };
    page.on('request', onReq);
    try {
        await page.evaluate(() => {
            // Override location.href setter via document.location since direct override fails
            const origAssign = window.location.assign;
            window.__navCapture = null;
            window.location.assign = function(u) { window.__navCapture = u; };
            window.location.replace = function(u) { window.__navCapture = u; };
            // Patch href setter: redefine via accessor on a copy is impossible.
            // Hack: use beforeunload to detect intent
            window.addEventListener('beforeunload', () => { /* no-op */ });
        });
        await clickFn();
        await new Promise(r => setTimeout(r, 800));
        captured = captured || await page.evaluate(() => window.__navCapture);
    } finally {
        page.off('request', onReq);
    }
    return captured;
}

async function run() {
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream']
    });
    const page = await browser.newPage();
    await page.setRequestInterception(true);
    page.on('request', (req) => {
        // Block actual navigation away from /chat to avoid disrupting test
        if (req.isNavigationRequest() && req.frame() === page.mainFrame() && !req.url().includes('/chat') && !req.url().includes('/static/') && !req.url().includes('/api/') && !req.url().includes('cdnjs')) {
            req.abort();
        } else {
            req.continue();
        }
    });

    const consoleErrors = [];
    page.on('pageerror', e => consoleErrors.push(`PAGE_ERR: ${e.message}`));
    page.on('console', m => {
        if (m.type() === 'error' && !m.text().includes('401') && !m.text().includes('ERR_FAILED')) {
            consoleErrors.push(`CONSOLE_ERR: ${m.text()}`);
        }
    });

    console.log('=== AUDIT NUT — http://localhost:8080/chat ===\n');

    const results = [];

    // === A. NUT KHONG NAVIGATE (reload truoc moi test) ===
    for (const btn of STAY_BUTTONS) {
        const r = { name: btn.name, id: btn.id, status: 'UNKNOWN', detail: '' };
        await loadPage(page, btn.viewport);
        try {
            const exists = await page.$(`#${btn.id}`);
            if (!exists) { r.status = '❌ NOT_FOUND'; results.push(r); continue; }

            const visible = await page.evaluate((id) => {
                const el = document.getElementById(id);
                if (!el) return false;
                const cs = getComputedStyle(el);
                return cs.display !== 'none' && cs.visibility !== 'hidden';
            }, btn.id);
            if (!visible) { r.status = '⚠️ HIDDEN'; r.detail = 'element invisible'; results.push(r); continue; }

            switch (btn.test) {
                case 'classToggle': {
                    const before = await page.$eval(btn.selector, (el, c) => el.classList.contains(c), btn.expectClass);
                    await page.evaluate((id) => document.getElementById(id).click(), btn.id);
                    await new Promise(r2 => setTimeout(r2, 300));
                    const after = await page.$eval(btn.selector, (el, c) => el.classList.contains(c), btn.expectClass);
                    if (before !== after) { r.status = '✅ OK'; r.detail = `${btn.expectClass}: ${before}→${after}`; }
                    else { r.status = '❌ NO_EFFECT'; r.detail = `class unchanged`; }
                    break;
                }
                case 'newChat': {
                    // Set 1 conversation roi click new chat
                    await page.evaluate(() => { Sidebar.currentConvId = 'fake-id'; });
                    await page.evaluate((id) => document.getElementById(id).click(), btn.id);
                    await new Promise(r2 => setTimeout(r2, 400));
                    const newId = await page.evaluate(() => Sidebar.currentConvId);
                    const welcomeShown = await page.evaluate(() => {
                        const w = document.getElementById('welcome');
                        return w && getComputedStyle(w).display !== 'none';
                    });
                    if (welcomeShown || newId !== 'fake-id') { r.status = '✅ OK'; r.detail = `welcome=${welcomeShown}, convId=${newId}`; }
                    else { r.status = '❌ NO_EFFECT'; r.detail = 'khong reset state'; }
                    break;
                }
                case 'showSearchBox': {
                    await page.evaluate((id) => document.getElementById(id).click(), btn.id);
                    await new Promise(r2 => setTimeout(r2, 250));
                    const visible = await page.evaluate(() => {
                        const box = document.querySelector('.search-box');
                        return box && getComputedStyle(box).display !== 'none';
                    });
                    r.status = visible ? '✅ OK' : '❌ NO_EFFECT';
                    r.detail = visible ? 'search box hien' : 'search box an';
                    break;
                }
                case 'shareCopy': {
                    await page.evaluateHandle(() => {
                        // Mock clipboard de tranh permission popup
                        navigator.clipboard.writeText = () => Promise.resolve();
                    });
                    await page.evaluate((id) => document.getElementById(id).click(), btn.id);
                    await new Promise(r2 => setTimeout(r2, 300));
                    const title = await page.$eval(`#${btn.id}`, el => el.title);
                    r.status = (title.includes('sao chép') || title.includes('Đã')) ? '✅ OK' : '⚠️ NO_FEEDBACK';
                    r.detail = `title="${title}"`;
                    break;
                }
                case 'darkToggle': {
                    const before = await page.evaluate(() => document.documentElement.outerHTML.substring(0, 200));
                    await page.evaluate((id) => document.getElementById(id).click(), btn.id);
                    await new Promise(r2 => setTimeout(r2, 250));
                    const after = await page.evaluate(() => document.documentElement.outerHTML.substring(0, 200));
                    const changed = before !== after;
                    if (changed) { r.status = '✅ OK'; r.detail = 'theme/class changed'; }
                    else { r.status = '❌ NO_THEME_TOGGLE'; r.detail = 'unchanged'; }
                    break;
                }
                case 'attachExists': {
                    // Check input + thuc su upload qua API
                    const has = await page.evaluate(() => !!document.querySelector('input[type="file"]'));
                    if (!has) { r.status = '❌ NO_FILE_INPUT'; r.detail = 'thieu input'; break; }
                    // Test upload thuc te qua /api/upload
                    const apiOk = await page.evaluate(async () => {
                        try {
                            const fd = new FormData();
                            fd.append('file', new Blob(['test'], { type: 'text/plain' }), 'test.txt');
                            const res = await fetch('/api/upload', { method: 'POST', body: fd });
                            const data = await res.json();
                            return res.ok && data.url ? data.url : null;
                        } catch (e) { return 'ERROR: ' + e.message; }
                    });
                    if (apiOk && apiOk.startsWith('/api/uploads/')) {
                        r.status = '✅ OK';
                        r.detail = `upload thanh cong → ${apiOk}`;
                    } else {
                        r.status = '⚠️ INPUT_OK_API_FAIL';
                        r.detail = `api upload: ${apiOk}`;
                    }
                    break;
                }
                case 'micToggle': {
                    await page.evaluate((id) => document.getElementById(id).click(), btn.id);
                    await new Promise(r2 => setTimeout(r2, 500));
                    const bg = await page.$eval(`#${btn.id}`, el => el.style.background);
                    r.status = bg ? '✅ OK (mic on)' : '⚠️ NO_VISIBLE_STATE';
                    r.detail = `background="${bg}"`;
                    break;
                }
                case 'voiceModeToggle': {
                    const before = await page.evaluate(() => Chat.voiceMode);
                    await page.evaluate((id) => document.getElementById(id).click(), btn.id);
                    await new Promise(r2 => setTimeout(r2, 400));
                    const after = await page.evaluate(() => Chat.voiceMode);
                    if (before !== after) { r.status = '✅ OK'; r.detail = `voiceMode ${before}→${after}`; }
                    else { r.status = '❌ NO_TOGGLE'; r.detail = `van ${after}`; }
                    break;
                }
                case 'sendEmpty': {
                    const disabled = await page.$eval(`#${btn.id}`, el => el.disabled);
                    const display = await page.$eval(`#${btn.id}`, el => getComputedStyle(el).display);
                    r.status = (disabled || display === 'none') ? '✅ OK' : '⚠️ ENABLED_KHI_RONG';
                    r.detail = `disabled=${disabled}, display=${display}`;
                    break;
                }
                case 'modelChange': {
                    const beforeLabel = await page.$eval(`#${btn.id}`, el => el.childNodes[0].textContent.trim());
                    const beforeModel = await page.evaluate(() => Chat.currentModel);
                    await page.evaluate((id) => document.getElementById(id).click(), btn.id);
                    await new Promise(r2 => setTimeout(r2, 250));
                    const afterLabel = await page.$eval(`#${btn.id}`, el => el.childNodes[0].textContent.trim());
                    const afterModel = await page.evaluate(() => Chat.currentModel);
                    if (beforeLabel !== afterLabel && (beforeModel !== afterModel || afterModel)) {
                        r.status = '✅ OK';
                        r.detail = `${beforeLabel}→${afterLabel}, Chat.currentModel=${afterModel}`;
                    } else if (beforeLabel !== afterLabel) {
                        r.status = '⚠️ COSMETIC';
                        r.detail = `label changed nhung Chat.currentModel khong set`;
                    } else {
                        r.status = '❌ NO_EFFECT';
                        r.detail = 'unchanged';
                    }
                    break;
                }
            }
        } catch (e) {
            r.status = '💥 ERROR';
            r.detail = e.message.substring(0, 80);
        }
        results.push(r);
    }

    // === B. NAVIGATE BUTTONS — capture qua request interception ===
    const navResults = [];
    for (const btn of NAVIGATE_BUTTONS) {
        const r = { name: btn.name, id: btn.id, status: 'UNKNOWN', detail: '' };
        await loadPage(page);
        try {
            const navUrl = await captureNavigation(page, async () => {
                await page.evaluate((id) => document.getElementById(id).click(), btn.id);
            });
            if (navUrl && navUrl.includes(btn.expectUrl)) {
                r.status = '✅ OK';
                r.detail = `→ ${navUrl}`;
            } else if (navUrl) {
                r.status = '⚠️ WRONG_URL';
                r.detail = `→ ${navUrl}`;
            } else {
                r.status = '❌ NO_HANDLER';
                r.detail = 'click khong gay navigation';
            }
        } catch (e) {
            r.status = '💥 ERROR';
            r.detail = e.message.substring(0, 80);
        }
        navResults.push(r);
    }

    for (const btn of NAVIGATE_NAV_BUTTONS) {
        const r = { name: btn.name, status: 'UNKNOWN', detail: '' };
        await loadPage(page);
        try {
            const navUrl = await captureNavigation(page, async () => {
                await page.evaluate((idx) => {
                    const items = document.querySelectorAll('.sidebar-nav .sidebar-btn');
                    if (items[idx]) items[idx].click();
                }, btn.idx);
            });
            if (navUrl && navUrl.includes(btn.expectUrl)) {
                r.status = '✅ OK';
                r.detail = `→ ${navUrl}`;
            } else if (navUrl) {
                r.status = '⚠️ WRONG_URL';
                r.detail = `→ ${navUrl}`;
            } else {
                r.status = '❌ NO_HANDLER';
                r.detail = 'click khong gay navigation';
            }
        } catch (e) {
            r.status = '💥 ERROR';
            r.detail = e.message.substring(0, 80);
        }
        navResults.push(r);
    }

    // === C. MY GPTS — click phai chuyen welcome + set Chat.activeSystemPrompt ===
    const gptResults = [];
    await loadPage(page);
    for (const gpt of GPT_ITEMS) {
        const r = { name: gpt.name, status: 'UNKNOWN', detail: '' };
        try {
            const beforeWelcome = await page.evaluate(() => document.getElementById('welcome')?.innerHTML.substring(0, 50) || '');
            await page.evaluate((idx) => {
                const items = document.querySelectorAll('#gptList .gpt-item');
                if (items[idx]) items[idx].click();
            }, gpt.idx);
            await new Promise(r2 => setTimeout(r2, 300));
            const afterWelcome = await page.evaluate(() => document.getElementById('welcome')?.innerHTML.substring(0, 80) || '');
            const sysPrompt = await page.evaluate(() => Chat.activeSystemPrompt);
            const presetName = await page.evaluate(() => Chat.activePresetName);
            const welcomeChanged = beforeWelcome !== afterWelcome;
            const promptSet = !!sysPrompt;
            if (welcomeChanged && promptSet) {
                r.status = '✅ OK';
                r.detail = `preset="${presetName}", prompt set (${sysPrompt.length} chars)`;
            } else {
                r.status = '❌ NO_EFFECT';
                r.detail = `welcome=${welcomeChanged}, prompt=${promptSet}`;
            }
        } catch (e) {
            r.status = '💥 ERROR';
            r.detail = e.message.substring(0, 80);
        }
        gptResults.push(r);
    }

    // Test them: nut + (tao GPT moi)
    await loadPage(page);
    try {
        const before = await page.evaluate(() => document.querySelectorAll('#gptList .gpt-item').length);
        await page.evaluate(() => document.getElementById('gptAddBtn')?.click());
        await new Promise(r2 => setTimeout(r2, 300));
        const modalOpen = await page.evaluate(() => !!document.querySelector('.gpt-modal-overlay'));
        gptResults.push({
            name: 'Nút + Tạo GPT',
            status: modalOpen ? '✅ OK' : '❌ NO_MODAL',
            detail: modalOpen ? `mo modal, hien tai ${before} GPT` : 'khong mo modal'
        });
    } catch (e) {
        gptResults.push({ name: 'Nút + Tạo GPT', status: '💥 ERROR', detail: e.message.substring(0, 80) });
    }

    // Test sua + xoa
    await loadPage(page);
    try {
        // Hover row 0 de hien actions
        await page.evaluate(() => {
            const row = document.querySelectorAll('#gptList .gpt-row')[0];
            if (row) row.querySelector('.gpt-actions').style.display = 'flex';
        });
        const editBtn = await page.evaluate(() => {
            const row = document.querySelectorAll('#gptList .gpt-row')[0];
            return row ? !!row.querySelector('.gpt-action-btn[title="Sửa"]') : false;
        });
        const delBtn = await page.evaluate(() => {
            const row = document.querySelectorAll('#gptList .gpt-row')[0];
            return row ? !!row.querySelector('.gpt-action-btn[title="Xóa"]') : false;
        });
        gptResults.push({
            name: 'Nút Sửa GPT',
            status: editBtn ? '✅ OK (rendered)' : '❌ NOT_FOUND',
            detail: editBtn ? 'co button sua' : 'thieu'
        });
        gptResults.push({
            name: 'Nút Xóa GPT',
            status: delBtn ? '✅ OK (rendered)' : '❌ NOT_FOUND',
            detail: delBtn ? 'co button xoa' : 'thieu'
        });
    } catch (e) {
        gptResults.push({ name: 'Edit/Delete GPT', status: '💥 ERROR', detail: e.message.substring(0, 80) });
    }

    // === D. MESSAGE BUTTONS ===
    const msgResults = [];
    await loadPage(page);
    try {
        await page.evaluate(() => {
            Chat.appendMessage('user', 'Test message');
            Chat.appendMessage('assistant', 'Test reply');
        });
        await new Promise(r => setTimeout(r, 200));

        const editBtn = await page.evaluate(() => {
            const btns = document.querySelectorAll('.message.user .msg-action-btn');
            return btns.length > 0 ? btns[0].title || 'edit' : null;
        });
        msgResults.push({
            name: 'Edit (user msg)',
            status: editBtn ? '✅ OK (rendered)' : '❌ NOT_FOUND',
            detail: editBtn ? `title="${editBtn}"` : 'thieu button'
        });

        const assistBtns = await page.evaluate(() => {
            const btns = document.querySelectorAll('.message.assistant .msg-action-btn');
            return Array.from(btns).map(b => b.title);
        });
        msgResults.push({
            name: 'Copy (assistant)',
            status: assistBtns.some(t => t.includes('hép') || t.includes('opy')) ? '✅ OK (rendered)' : '❌ NOT_FOUND',
            detail: assistBtns.join(', ')
        });
        msgResults.push({
            name: 'Regenerate (assistant)',
            status: assistBtns.some(t => t.includes('ạo lại') || t.includes('egen')) ? '✅ OK (rendered)' : '❌ NOT_FOUND',
            detail: assistBtns.join(', ')
        });
    } catch (e) {
        msgResults.push({ name: 'Message buttons', status: '💥 ERROR', detail: e.message.substring(0, 80) });
    }

    // === E. CONVERSATION ITEMS ===
    const convResults = [];
    await loadPage(page);
    await new Promise(r => setTimeout(r, 1000));
    try {
        const convCount = await page.evaluate(() => document.querySelectorAll('#conversationList .conv-item').length);
        const delBtnCount = await page.evaluate(() => document.querySelectorAll('#conversationList .delete-btn').length);
        convResults.push({
            name: 'Conversation items + delete',
            status: convCount > 0 ? '✅ OK' : '⚠️ EMPTY',
            detail: `${convCount} conv, ${delBtnCount} delete btn`
        });
    } catch (e) {
        convResults.push({ name: 'Conversations', status: '💥 ERROR', detail: e.message.substring(0, 80) });
    }

    // === IN BAO CAO ===
    function printSection(title, arr) {
        console.log(`\n## ${title}\n`);
        arr.forEach((r, i) => {
            console.log(`${(i+1).toString().padStart(2)}. ${r.status.padEnd(34)} ${r.name.padEnd(28)} | ${r.detail}`);
        });
    }

    console.log('\n┌─────────────────────────────────────────────────────────────────┐');
    console.log('│              KET QUA AUDIT TUNG NUT                              │');
    console.log('└─────────────────────────────────────────────────────────────────┘');

    printSection('A. NUT TINH (KHONG navigate)', results);
    printSection('B. NUT NAVIGATE', navResults);
    printSection('C. 4 GPT ITEMS HARDCODE', gptResults);
    printSection('D. NUT TRONG MESSAGE', msgResults);
    printSection('E. CONVERSATION ITEMS', convResults);

    if (consoleErrors.length > 0) {
        console.log('\n## F. CONSOLE ERRORS:');
        [...new Set(consoleErrors)].slice(0, 10).forEach(e => console.log(`  • ${e}`));
    } else {
        console.log('\n## F. CONSOLE: 0 errors ✅');
    }

    const all = [...results, ...navResults, ...gptResults, ...msgResults, ...convResults];
    const ok = all.filter(r => r.status.includes('✅')).length;
    const partial = all.filter(r => r.status.includes('⚠️')).length;
    const dead = all.filter(r => r.status.includes('🔴') || r.status.includes('❌') || r.status.includes('💥')).length;

    console.log('\n┌─────────────────────────────────────────────────────────────────┐');
    console.log(`│  TONG: ${all.length} nut | ✅ ${ok} OK | ⚠️ ${partial} nua voi | ❌ ${dead} loi  │`);
    console.log('└─────────────────────────────────────────────────────────────────┘');

    await browser.close();
}

run().catch(e => { console.error('FATAL:', e); process.exit(1); });
