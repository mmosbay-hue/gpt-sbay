"""Pipeline — Full automated flow: Meeting → Build → Test → Report."""
import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.meeting import run_full_meeting
from agents.builder import execute_all_tasks
from agents.llm_router import call_agent

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
REPORT_DIR = os.path.join(PROJECT_ROOT, "message_bus", "claude_inbox")


def run_qa_review(build_results: list[dict]) -> dict:
    """QA review of build results — check all files for issues."""
    print("\n" + "=" * 60)
    print("🔍 QA REVIEW — Kiểm tra code sau build")
    print("=" * 60)

    # Read all key files
    files_to_check = [
        "backend/main.py",
        "backend/chat.py",
        "backend/deepseek_client.py",
        "backend/sessions.py",
        "backend/config.py",
        "backend/models.py",
        "frontend/index.html",
        "frontend/css/style.css",
        "frontend/js/app.js",
        "frontend/js/chat.js",
        "frontend/js/sidebar.js",
        "frontend/js/markdown.js",
    ]

    all_code = ""
    for fp in files_to_check:
        full = os.path.join(PROJECT_ROOT, fp)
        if os.path.exists(full):
            with open(full, "r", encoding="utf-8") as f:
                content = f.read()
            all_code += f"\n\n=== {fp} ===\n{content}"

    # QA agent reviews
    review = call_agent(
        system_prompt="""You are a senior QA engineer reviewing a ChatGPT-clone web app.
Check for:
1. Import errors or broken references
2. Missing functionality
3. UI/UX issues
4. Security issues
5. Performance issues

Output as JSON:
{
  "status": "pass" or "fail",
  "issues": [{"file": "...", "line": N, "severity": "critical/warning/info", "issue": "...", "fix": "..."}],
  "score": 0-100
}""",
        user_prompt=f"Review these files:\n{all_code[:6000]}",
        max_tokens=1000
    )

    try:
        start = review.find('{')
        end = review.rfind('}') + 1
        if start >= 0 and end > start:
            qa_result = json.loads(review[start:end])
        else:
            qa_result = {"status": "unknown", "issues": [], "score": 50}
    except json.JSONDecodeError:
        qa_result = {"status": "unknown", "raw_review": review[:500], "issues": [], "score": 50}

    print(f"   📊 QA Score: {qa_result.get('score', '?')}/100")
    print(f"   Status: {qa_result.get('status', '?')}")
    if qa_result.get("issues"):
        for issue in qa_result["issues"][:5]:
            print(f"   ⚠️ [{issue.get('severity', '?')}] {issue.get('file', '?')}: {issue.get('issue', '?')[:60]}")

    return qa_result


def save_pipeline_report(meeting: dict, build: list, qa: dict):
    """Save final pipeline report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "meeting_completed": bool(meeting),
        "tasks_total": len(build),
        "tasks_done": sum(1 for b in build if b.get("status") == "done"),
        "qa_score": qa.get("score", 0),
        "qa_status": qa.get("status", "unknown"),
        "issues_count": len(qa.get("issues", [])),
        "critical_issues": [i for i in qa.get("issues", []) if i.get("severity") == "critical"],
    }

    path = os.path.join(REPORT_DIR, f"pipeline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📄 Report saved: {path}")
    return report


def run_pipeline():
    """Run the full pipeline."""
    print("\n" + "🚀" * 30)
    print("PIPELINE START — GPT Web ChatGPT Clone")
    print("🚀" * 30)

    # Phase 1: Meeting
    meeting = run_full_meeting()

    # Phase 2: Build
    tasks = meeting.get("tasks", [])
    build_results = execute_all_tasks(tasks) if tasks else []

    # Phase 3: QA Review
    qa_result = run_qa_review(build_results)

    # Phase 4: Report
    report = save_pipeline_report(meeting, build_results, qa_result)

    print("\n" + "=" * 60)
    print(f"🏁 PIPELINE COMPLETE")
    print(f"   Tasks: {report['tasks_done']}/{report['tasks_total']}")
    print(f"   QA: {report['qa_score']}/100 ({report['qa_status']})")
    print(f"   Critical issues: {len(report['critical_issues'])}")
    print("=" * 60)

    return report


if __name__ == "__main__":
    run_pipeline()
