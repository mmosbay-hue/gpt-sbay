"""Agent Meeting Room — 2-way discussion before coding.

Flow:
1. Claude sends project brief to all Directors
2. Each Director analyzes and responds with their perspective
3. Directors discuss with each other (cross-review)
4. Consensus reached → task breakdown → workers assigned
5. Workers confirm understanding → start coding
"""
import json
import os
from datetime import datetime
from agents.agent_core import Agent
from agents.agent_factory import create_all_agents, get_directors, get_builders, get_testers
from agents.llm_router import call_agent, call_agent_with_history

MEETING_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "message_bus", "meeting_room")
os.makedirs(MEETING_DIR, exist_ok=True)

PROJECT_BRIEF = """
# GPT Web — ChatGPT Clone

## Mục tiêu
Xây web chat UI/UX giống ChatGPT, dùng DeepSeek API.

## Stack
- Backend: Python FastAPI, SSE streaming
- Frontend: Vanilla HTML/CSS/JS (no framework)
- LLM: DeepSeek API (OpenAI SDK compatible)
- Theme: Dark mode giống ChatGPT

## Features MVP
1. Chat với streaming responses (SSE)
2. Dark theme giống ChatGPT
3. Markdown rendering + syntax highlighting
4. Conversation history sidebar (grouped by date)
5. New chat / delete chat
6. Copy code button
7. Responsive mobile
8. Auto-scroll
9. Textarea auto-resize
10. LocalStorage cho conversations (future)

## Cấu trúc đã có
- backend/: FastAPI app + DeepSeek client + sessions + models
- frontend/: index.html + style.css + chat.js + sidebar.js + markdown.js + app.js
- Cần: review, test, fix bugs, polish

## Yêu cầu
- Code phải chạy được ngay (no broken imports)
- UI phải pixel-perfect giống ChatGPT
- Streaming phải smooth, không lag
- Code blocks phải có syntax highlighting + copy button
"""


def save_meeting_log(phase: str, messages: list[dict]):
    """Save meeting discussion to file."""
    path = os.path.join(MEETING_DIR, f"{phase}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def run_director_meeting() -> dict:
    """Phase 1: Directors analyze project and give perspectives."""
    agents = create_all_agents()
    directors = get_directors(agents)

    meeting_log = []
    director_opinions = {}

    print("\n🏛️  DIRECTOR MEETING — Phân tích dự án")
    print("=" * 60)

    # Each director analyzes the brief
    for director in directors:
        print(f"\n📋 {director.name} đang phân tích...")

        response = call_agent(
            system_prompt=director.system_prompt + "\n\nYou are in a meeting. Analyze this project brief. Identify: (1) What's good, (2) What's missing/wrong, (3) Your recommendations. Be specific with file names and code. Max 300 words.",
            user_prompt=PROJECT_BRIEF,
            max_tokens=500
        )

        director.remember("project_brief", "Analyzed GPT Web project")
        director.remember("meeting_opinion", response[:200])

        director_opinions[director.id] = response
        meeting_log.append({
            "agent": director.name,
            "role": director.role,
            "phase": "analysis",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })

        print(f"   ✅ {director.name}: {response[:100]}...")

    # Cross-review: each director reviews others' opinions
    print("\n\n🔄 CROSS-REVIEW — Directors thảo luận 2 chiều")
    print("=" * 60)

    all_opinions = "\n\n".join([
        f"**{agents[did].name}** ({agents[did].role}):\n{opinion}"
        for did, opinion in director_opinions.items()
    ])

    consensus = {}
    for director in directors:
        print(f"\n💬 {director.name} đang review ý kiến đồng nghiệp...")

        response = call_agent(
            system_prompt=director.system_prompt + "\n\nReview your colleagues' opinions below. Agree or disagree with specific points. Propose final action items for YOUR area. Be specific with file names. Max 200 words.",
            user_prompt=f"Your original analysis:\n{director_opinions[director.id]}\n\nAll directors' opinions:\n{all_opinions}",
            max_tokens=400
        )

        consensus[director.id] = response
        meeting_log.append({
            "agent": director.name,
            "role": director.role,
            "phase": "cross_review",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })

        print(f"   ✅ {director.name}: {response[:100]}...")

    save_meeting_log("director_meeting", meeting_log)

    return {
        "opinions": director_opinions,
        "consensus": consensus,
        "meeting_log": meeting_log
    }


def run_task_assignment(director_consensus: dict) -> list[dict]:
    """Phase 2: Tech Architect breaks down into tasks for builders."""
    agents = create_all_agents()
    tech_arch = agents["dir_tech"]

    print("\n\n📋 TASK ASSIGNMENT — Tech Architect phân việc")
    print("=" * 60)

    consensus_text = "\n\n".join([
        f"**{agents[did].name}**: {opinion}"
        for did, opinion in director_consensus.items()
    ])

    response = call_agent(
        system_prompt=tech_arch.system_prompt + """

Based on the meeting consensus, create a task list for builders.
Output as JSON array:
[
  {"task_id": "T1", "file": "backend/chat.py", "description": "...", "assigned_to": "build_backend_stream", "priority": 1},
  ...
]
Only output the JSON array, no other text.""",
        user_prompt=f"Meeting consensus:\n{consensus_text}\n\nProject brief:\n{PROJECT_BRIEF}\n\nAvailable builders: build_backend_api, build_backend_stream, build_frontend_css, build_frontend_chat, build_frontend_sidebar, build_markdown\nAvailable testers: test_e2e, test_edge, test_puppeteer",
        max_tokens=800
    )

    # Parse tasks
    try:
        # Find JSON in response
        start = response.find('[')
        end = response.rfind(']') + 1
        if start >= 0 and end > start:
            tasks = json.loads(response[start:end])
        else:
            tasks = []
    except json.JSONDecodeError:
        tasks = []

    # Fallback to defaults if no tasks parsed
    if not tasks:
        print(f"   ⚠️ Using default task list")
        tasks = [
            {"task_id": "T1", "file": "backend/chat.py", "description": "Review and fix SSE streaming endpoint — ensure proper error handling, conversation_id flow, and system prompt", "assigned_to": "build_backend_stream", "priority": 1},
            {"task_id": "T2", "file": "frontend/css/style.css", "description": "Polish ChatGPT dark theme — match exact ChatGPT colors, spacing, scrollbar, message bubbles, responsive", "assigned_to": "build_frontend_css", "priority": 1},
            {"task_id": "T3", "file": "frontend/js/chat.js", "description": "Fix streaming display — smooth token append, typing indicator removal, error display, auto-scroll behavior", "assigned_to": "build_frontend_chat", "priority": 1},
            {"task_id": "T4", "file": "frontend/js/sidebar.js", "description": "Fix conversation list — proper date grouping, active state, delete with confirmation, refresh after actions", "assigned_to": "build_frontend_sidebar", "priority": 2},
            {"task_id": "T5", "file": "frontend/js/markdown.js", "description": "Fix code block rendering — proper language detection, copy button, inline code styling", "assigned_to": "build_markdown", "priority": 2},
            {"task_id": "T6", "file": "backend/sessions.py", "description": "Add LocalStorage sync endpoint — export/import conversations for persistence", "assigned_to": "build_backend_api", "priority": 3},
        ]

    print(f"   📝 {len(tasks)} tasks assigned")
    for t in tasks:
        print(f"   [{t.get('priority', '?')}] {t.get('task_id', '?')}: {t.get('description', '?')[:60]} → {t.get('assigned_to', '?')}")

    save_meeting_log("task_assignment", tasks)
    return tasks


def run_builder_confirm(tasks: list[dict]) -> dict:
    """Phase 3: Builders confirm they understand their tasks."""
    agents = create_all_agents()
    confirmations = {}

    print("\n\n✋ BUILDER CONFIRMATION — Workers xác nhận hiểu task")
    print("=" * 60)

    for task in tasks:
        builder_id = task.get("assigned_to", "")
        if builder_id not in agents:
            continue

        builder = agents[builder_id]

        # Read the actual file if it exists
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), task.get("file", ""))
        file_content = ""
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()

        response = call_agent(
            system_prompt=builder.system_prompt + "\n\nYou received a task. Read the current code. Confirm you understand. List exactly what you will change (line numbers if possible). If you have questions, ask them. Max 150 words.",
            user_prompt=f"Task: {task.get('description', '')}\nFile: {task.get('file', '')}\n\nCurrent code:\n```\n{file_content[:2000]}\n```",
            max_tokens=300
        )

        builder.remember("task_assigned", task.get("description", ""))
        confirmations[builder_id] = {
            "task": task,
            "confirmation": response
        }

        print(f"   ✅ {builder.name}: {response[:80]}...")

    save_meeting_log("builder_confirmations", list(confirmations.values()))
    return confirmations


def run_full_meeting() -> dict:
    """Run the complete meeting flow: Directors → Tasks → Builder Confirm."""
    print("\n" + "=" * 60)
    print("🚀 AGENT MEETING — BẮT ĐẦU")
    print("=" * 60)

    # Phase 1: Director meeting
    result = run_director_meeting()

    # Phase 2: Task assignment
    tasks = run_task_assignment(result["consensus"])

    # Phase 3: Builder confirmation
    confirmations = run_builder_confirm(tasks)

    print("\n\n" + "=" * 60)
    print("✅ MEETING HOÀN TẤT — Agents đã hiểu 100%, sẵn sàng code!")
    print("=" * 60)

    return {
        "director_meeting": result,
        "tasks": tasks,
        "confirmations": confirmations
    }


if __name__ == "__main__":
    run_full_meeting()
