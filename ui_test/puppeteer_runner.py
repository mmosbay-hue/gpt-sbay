"""Puppeteer Test Runner — goi Node.js Puppeteer tu Python."""
import subprocess
import os
import sys
import json
import logging
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).parent.parent)
PUPPETEER_DIR = os.path.join(PROJECT_ROOT, "puppeteer")
SCREENSHOT_DIR = os.path.join(PROJECT_ROOT, "ui_test", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

log = logging.getLogger("puppeteer")


def run_puppeteer_script(script_name: str) -> dict:
    """Run a Puppeteer Node.js script and return results."""
    script_path = os.path.join(PUPPETEER_DIR, script_name)
    if not os.path.exists(script_path):
        return {"status": "error", "message": f"Script not found: {script_path}"}

    try:
        result = subprocess.run(
            ["node", script_path],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=PUPPETEER_DIR,
        )
        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"status": "ok", "output": result.stdout[:500]}
        else:
            return {"status": "error", "stderr": result.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except FileNotFoundError:
        return {"status": "error", "message": "Node.js not found"}


def take_screenshot(url: str = "http://localhost:8080", name: str = "screenshot") -> str:
    """Take a screenshot using Puppeteer."""
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"{name}.png")

    script = f"""
const puppeteer = require('puppeteer');
(async () => {{
    const browser = await puppeteer.launch({{ headless: 'new', args: ['--no-sandbox'] }});
    const page = await browser.newPage();
    await page.setViewport({{ width: 1440, height: 900 }});
    await page.goto('{url}', {{ waitUntil: 'networkidle0', timeout: 15000 }});
    await page.screenshot({{ path: '{screenshot_path.replace(os.sep, "/")}', fullPage: false }});
    await browser.close();
    console.log(JSON.stringify({{ status: 'ok', path: '{screenshot_path.replace(os.sep, "/")}' }}));
}})();
"""
    temp_script = os.path.join(PUPPETEER_DIR, "_temp_screenshot.js")
    with open(temp_script, "w") as f:
        f.write(script)

    result = run_puppeteer_script("_temp_screenshot.js")
    os.remove(temp_script) if os.path.exists(temp_script) else None

    return screenshot_path if result.get("status") == "ok" else ""


def test_chat_flow(url: str = "http://localhost:8080") -> dict:
    """Test the complete chat flow: load → type → send → receive."""
    script = f"""
const puppeteer = require('puppeteer');
(async () => {{
    const results = {{ tests: [], passed: 0, failed: 0 }};
    const browser = await puppeteer.launch({{ headless: 'new', args: ['--no-sandbox'] }});
    const page = await browser.newPage();
    await page.setViewport({{ width: 1440, height: 900 }});

    // Test 1: Page loads
    try {{
        await page.goto('{url}', {{ waitUntil: 'networkidle0', timeout: 15000 }});
        results.tests.push({{ name: 'page_load', status: 'pass' }});
        results.passed++;
    }} catch (e) {{
        results.tests.push({{ name: 'page_load', status: 'fail', error: e.message }});
        results.failed++;
    }}

    // Test 2: Welcome screen visible
    try {{
        const welcome = await page.$('.welcome');
        if (welcome) {{
            results.tests.push({{ name: 'welcome_visible', status: 'pass' }});
            results.passed++;
        }} else {{
            throw new Error('Welcome not found');
        }}
    }} catch (e) {{
        results.tests.push({{ name: 'welcome_visible', status: 'fail', error: e.message }});
        results.failed++;
    }}

    // Test 3: Input exists and is focusable
    try {{
        const input = await page.$('#messageInput');
        if (input) {{
            await input.focus();
            results.tests.push({{ name: 'input_focus', status: 'pass' }});
            results.passed++;
        }} else {{
            throw new Error('Input not found');
        }}
    }} catch (e) {{
        results.tests.push({{ name: 'input_focus', status: 'fail', error: e.message }});
        results.failed++;
    }}

    // Test 4: Sidebar visible
    try {{
        const sidebar = await page.$('.sidebar');
        if (sidebar) {{
            results.tests.push({{ name: 'sidebar_visible', status: 'pass' }});
            results.passed++;
        }} else {{
            throw new Error('Sidebar not found');
        }}
    }} catch (e) {{
        results.tests.push({{ name: 'sidebar_visible', status: 'fail', error: e.message }});
        results.failed++;
    }}

    // Test 5: New Chat button works
    try {{
        await page.click('.new-chat-btn');
        await page.waitForTimeout(500);
        results.tests.push({{ name: 'new_chat_btn', status: 'pass' }});
        results.passed++;
    }} catch (e) {{
        results.tests.push({{ name: 'new_chat_btn', status: 'fail', error: e.message }});
        results.failed++;
    }}

    // Test 6: Send a message
    try {{
        await page.type('#messageInput', 'Hello test');
        await page.waitForTimeout(200);
        await page.click('.send-btn');
        await page.waitForTimeout(3000); // Wait for streaming
        const messages = await page.$$('.message');
        if (messages.length >= 1) {{
            results.tests.push({{ name: 'send_message', status: 'pass' }});
            results.passed++;
        }} else {{
            throw new Error('No messages appeared');
        }}
    }} catch (e) {{
        results.tests.push({{ name: 'send_message', status: 'fail', error: e.message }});
        results.failed++;
    }}

    // Screenshot final state
    await page.screenshot({{ path: '{SCREENSHOT_DIR.replace(os.sep, "/")}/test_result.png' }});

    await browser.close();
    console.log(JSON.stringify(results));
}})();
"""
    temp_script = os.path.join(PUPPETEER_DIR, "_temp_test.js")
    with open(temp_script, "w") as f:
        f.write(script)

    result = run_puppeteer_script("_temp_test.js")
    os.remove(temp_script) if os.path.exists(temp_script) else None

    return result


if __name__ == "__main__":
    # Quick test
    print("Testing chat flow...")
    result = test_chat_flow()
    print(json.dumps(result, indent=2))
