const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
    const page = await browser.newPage();
    page.on('console', m => console.log(`[${m.type()}]`, m.text()));
    page.on('pageerror', e => console.log('PAGE_ERR:', e.message));
    await page.goto('http://localhost:8080/chat', { waitUntil: 'domcontentloaded' });
    await new Promise(r => setTimeout(r, 800));

    const debug = await page.evaluate(() => {
        const out = {};
        out.MyGptsExists = !!window.MyGpts;
        out.ChatExists = !!window.Chat;
        out.SidebarExists = !!window.Sidebar;
        out.itemsCount = MyGpts.items.length;
        out.firstItem = MyGpts.items[0];
        out.gptListChildren = document.querySelectorAll('#gptList .gpt-item').length;

        // Click first item
        const items = document.querySelectorAll('#gptList .gpt-item');
        if (items.length > 0) {
            items[0].click();
            out.afterClick = {
                activeSystemPrompt: Chat.activeSystemPrompt,
                activePresetName: Chat.activePresetName,
                welcomeHTML: document.getElementById('welcome')?.innerHTML.substring(0, 100),
            };
        }
        return out;
    });
    console.log(JSON.stringify(debug, null, 2));
    await browser.close();
})();
