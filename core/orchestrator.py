"""
PYTHON ORCHESTRATOR — AI Operating System
Dieu phoi toan bo he thong: DeepSeek + Agents + Puppeteer + Server
Auto loop: analyze → code → test → fix → repeat
"""
import json
import os
import sys
import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.deepseek import ask, generate_code, analyze, debug as ai_debug

# ============ CONFIG ============
PROJECT_ROOT = str(Path(__file__).parent.parent)
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "system.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("orchestrator")

# Key project files
KEY_FILES = {
    "backend/main.py": "FastAPI app",
    "backend/chat.py": "Chat SSE streaming",
    "backend/deepseek_client.py": "DeepSeek API client",
    "backend/sessions.py": "Conversation management",
    "backend/config.py": "Config",
    "backend/models.py": "Pydantic models",
    "frontend/index.html": "Main HTML",
    "frontend/css/style.css": "ChatGPT dark theme CSS",
    "frontend/js/app.js": "App orchestrator JS",
    "frontend/js/chat.js": "Chat UI + streaming JS",
    "frontend/js/sidebar.js": "Sidebar JS",
    "frontend/js/markdown.js": "Markdown renderer JS",
}

# Memory: error history
ERROR_HISTORY = []
FIX_PATTERNS = {}


# ============ FILE OPS ============
def read_file(rel_path: str) -> str:
    path = os.path.join(PROJECT_ROOT, rel_path)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def write_file(rel_path: str, content: str):
    path = os.path.join(PROJECT_ROOT, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    log.info(f"Written: {rel_path}")


def read_all_files() -> str:
    content = ""
    for fp, desc in KEY_FILES.items():
        code = read_file(fp)
        if code:
            content += f"\n\n=== {fp} ({desc}) ===\n{code}"
    return content


# ============ SERVER ============
def check_server() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:8080/api/conversations", timeout=5)
        return True
    except Exception:
        return False


def start_server():
    if check_server():
        log.info("Server already running")
        return True

    log.info("Starting server...")
    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    time.sleep(3)
    ok = check_server()
    log.info(f"Server: {'OK' if ok else 'FAILED'}")
    return ok


# ============ QA SCORING ============
def run_qa_scoring(all_code: str) -> dict:
    """6 agents score the project."""
    log.info("Running QA scoring (6 agents)...")

    agents = {
        "layout": "Score LAYOUT (0-25): sidebar 260px, chat center 768px, input bottom, header minimal. Check CSS file.",
        "typography": "Score TYPOGRAPHY (0-15): font Söhne/system-ui, sizes 14-16-18px, line-height 1.5-1.75. Check CSS.",
        "color": "Score COLOR (0-10): dark mode exact — bg #343541, sidebar #202123, text #ececf1, hover #2a2b32. Check CSS.",
        "interaction": "Score INTERACTION (0-25): Enter send/Shift+Enter newline, auto-scroll, SSE streaming, focus input, typing indicator. Check JS.",
        "performance": "Score PERFORMANCE (0-15): no console errors, clean code, no dead code, proper error handling. Check all files.",
        "ux_feeling": "Score UX FEELING (0-10): avatar+role label on messages, code block copy button, responsive mobile, smooth animations. Check HTML+CSS+JS.",
    }

    total = 0
    details = {}

    for agent_name, prompt in agents.items():
        response = ask(
            system=f"You are a QA scoring agent. {prompt}\nOutput ONLY a JSON: {{\"score\": N, \"issues\": [\"...\"], \"suggestions\": [\"...\"]}}",
            user=f"Review this code:\n{all_code[:4000]}",
            max_tokens=300,
        )

        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(response[start:end])
                score = result.get("score", 0)
                total += score
                details[agent_name] = result
                log.info(f"  {agent_name}: {score}")
            else:
                details[agent_name] = {"score": 0, "raw": response[:100]}
        except Exception:
            details[agent_name] = {"score": 0, "raw": response[:100]}

    log.info(f"Total QA Score: {total}/100")
    return {"total": total, "details": details}


# ============ AUTO FIX ============
def fix_issues(qa_result: dict, all_code: str) -> list:
    """Fix issues found by QA agents."""
    fixes = []

    for agent_name, detail in qa_result.get("details", {}).items():
        issues = detail.get("issues", [])
        suggestions = detail.get("suggestions", [])

        if not issues and not suggestions:
            continue

        # Determine which file to fix based on agent type
        file_map = {
            "layout": "frontend/css/style.css",
            "typography": "frontend/css/style.css",
            "color": "frontend/css/style.css",
            "interaction": "frontend/js/chat.js",
            "performance": "backend/chat.py",
            "ux_feeling": "frontend/index.html",
        }

        target_file = file_map.get(agent_name, "")
        if not target_file:
            continue

        current_code = read_file(target_file)
        if not current_code:
            continue

        task = f"Fix these issues in {target_file}:\n"
        for issue in issues[:3]:
            task += f"- {issue}\n"
        for sug in suggestions[:2]:
            task += f"- Suggestion: {sug}\n"

        log.info(f"Fixing {target_file}: {len(issues)} issues")

        fixed_code = generate_code(task, current_code)
        if fixed_code and not fixed_code.startswith("[ERROR]"):
            # Strip markdown fences
            code = fixed_code.strip()
            if code.startswith("```"):
                lines = code.split("\n")
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                code = "\n".join(lines)

            write_file(target_file, code)
            fixes.append({"file": target_file, "agent": agent_name, "issues_fixed": len(issues)})

    return fixes


# ============ SELF-HEALING ============
def self_heal(error: str, file_path: str):
    """Auto-fix errors using AI debug."""
    log.warning(f"Self-healing: {error[:100]}")

    current_code = read_file(file_path)
    if not current_code:
        return

    fixed = ai_debug(error, current_code)
    if fixed and not fixed.startswith("[ERROR]"):
        code = fixed.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines)
        write_file(file_path, code)

        ERROR_HISTORY.append({
            "error": error[:200],
            "file": file_path,
            "fixed_at": datetime.now().isoformat(),
        })
        log.info(f"Self-healed: {file_path}")


# ============ MAIN CYCLE ============
def run_cycle() -> dict:
    """Run one complete orchestrator cycle."""
    cycle_start = datetime.now()
    log.info(f"\n{'='*60}")
    log.info(f"ORCHESTRATOR CYCLE — {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"{'='*60}")

    # 1. Ensure server
    start_server()

    # 2. Read all code
    all_code = read_all_files()
    log.info(f"Read {len(KEY_FILES)} files")

    # 3. QA Scoring (6 agents)
    qa = run_qa_scoring(all_code)
    score = qa["total"]

    # 4. Fix if below threshold
    fixes = []
    if score < 95:
        log.info(f"Score {score} < 95 — running auto-fix...")
        fixes = fix_issues(qa, all_code)
        log.info(f"Fixed {len(fixes)} files")

    # 5. Save report
    report = {
        "timestamp": cycle_start.isoformat(),
        "score": score,
        "completed": score >= 95,
        "fixes": fixes,
        "error_history_count": len(ERROR_HISTORY),
    }

    report_path = os.path.join(LOG_DIR, f"cycle_{cycle_start.strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log.info(f"Score: {score}/100 | Fixes: {len(fixes)} | Complete: {score >= 95}")
    return report


# ============ AUTO LOOP ============
def run_auto_loop(min_interval=300, max_interval=600):
    """Run continuous loop until score >= 95."""
    import random

    log.info("AUTO LOOP STARTED — running until 100% complete")

    while True:
        report = run_cycle()

        if report["completed"]:
            log.info("COMPLETED! Score >= 95. System stable.")
            break

        # Smart interval: shorter if more fixes needed
        if report["fixes"]:
            interval = min_interval
        else:
            interval = random.randint(min_interval, max_interval)

        log.info(f"Sleeping {interval}s before next cycle...")
        time.sleep(interval)


if __name__ == "__main__":
    if "--loop" in sys.argv:
        run_auto_loop()
    else:
        run_cycle()
