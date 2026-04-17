"""Builder — agents execute their assigned tasks by generating code fixes."""
import json
import os
from datetime import datetime
from agents.agent_core import Agent
from agents.agent_factory import create_all_agents
from agents.llm_router import call_agent

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
BUILD_LOG_DIR = os.path.join(PROJECT_ROOT, "message_bus", "claude_inbox")
os.makedirs(BUILD_LOG_DIR, exist_ok=True)


def read_file(relative_path: str) -> str:
    """Read a project file."""
    path = os.path.join(PROJECT_ROOT, relative_path)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def write_file(relative_path: str, content: str):
    """Write a project file."""
    path = os.path.join(PROJECT_ROOT, relative_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def execute_task(task: dict) -> dict:
    """Have a builder agent execute a single task."""
    agents = create_all_agents()
    builder_id = task.get("assigned_to", "")

    if builder_id not in agents:
        return {"status": "error", "message": f"Unknown agent: {builder_id}"}

    builder = agents[builder_id]
    file_path = task.get("file", "")
    current_code = read_file(file_path)

    print(f"\n🔧 {builder.name} đang code: {task.get('description', '')[:60]}")

    # Ask builder to generate the fixed code
    response = call_agent(
        system_prompt=builder.system_prompt + f"""

You are working on file: {file_path}
Task: {task.get('description', '')}

RULES:
- Output ONLY the complete updated file content
- Do NOT use markdown code fences
- Do NOT add explanations before or after the code
- The output must be valid, runnable code
- Keep all existing functionality intact
- Only change what the task requires""",
        user_prompt=f"Current file content:\n{current_code}",
        max_tokens=2000
    )

    # Validate response looks like code (not an error or explanation)
    if response.startswith("[ERROR]"):
        return {"status": "error", "message": response, "agent": builder.name}

    # Write the updated file
    # Strip markdown fences if present
    code = response.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        lines = lines[1:]  # remove first ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)

    write_file(file_path, code)
    builder.mark_task_done(task.get("description", ""))

    result = {
        "status": "done",
        "agent": builder.name,
        "file": file_path,
        "task": task.get("description", ""),
        "timestamp": datetime.now().isoformat()
    }

    # Log to claude inbox
    log_path = os.path.join(BUILD_LOG_DIR, f"build_{task.get('task_id', 'unknown')}_{datetime.now().strftime('%H%M%S')}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"   ✅ {builder.name} hoàn thành: {file_path}")
    return result


def execute_all_tasks(tasks: list[dict]) -> list[dict]:
    """Execute all tasks sequentially (priority order)."""
    sorted_tasks = sorted(tasks, key=lambda t: t.get("priority", 99))
    results = []

    print("\n" + "=" * 60)
    print("🏗️  BUILD PHASE — Agents bắt đầu code")
    print("=" * 60)

    for task in sorted_tasks:
        result = execute_task(task)
        results.append(result)

    done = sum(1 for r in results if r["status"] == "done")
    print(f"\n📊 Build complete: {done}/{len(results)} tasks done")

    return results
