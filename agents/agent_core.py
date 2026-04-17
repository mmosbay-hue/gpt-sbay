"""Agent Core — Brain + Memory + Skills for each agent."""
import json
import os
from datetime import datetime

AGENTS_DIR = os.path.dirname(__file__)
BRAINS_DIR = os.path.join(AGENTS_DIR, "brains")
MEMORIES_DIR = os.path.join(AGENTS_DIR, "memories")

os.makedirs(BRAINS_DIR, exist_ok=True)
os.makedirs(MEMORIES_DIR, exist_ok=True)


class Agent:
    def __init__(self, agent_id: str, name: str, role: str, tier: int, system_prompt: str):
        self.id = agent_id
        self.name = name
        self.role = role
        self.tier = tier  # 1=Director, 2=Designer, 3=Builder, 4=Tester
        self.system_prompt = system_prompt
        self.memory = self._load_memory()

    def _memory_path(self) -> str:
        return os.path.join(MEMORIES_DIR, f"{self.id}.json")

    def _load_memory(self) -> dict:
        path = self._memory_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"short_term": [], "long_term": [], "tasks_done": [], "insights": []}

    def save_memory(self):
        with open(self._memory_path(), "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2)

    def remember(self, key: str, content: str):
        """Add to short-term memory."""
        self.memory["short_term"].append({
            "key": key,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        # Keep last 20
        self.memory["short_term"] = self.memory["short_term"][-20:]
        self.save_memory()

    def add_insight(self, insight: str):
        self.memory["insights"].append({
            "content": insight,
            "timestamp": datetime.now().isoformat()
        })
        self.save_memory()

    def mark_task_done(self, task: str):
        self.memory["tasks_done"].append({
            "task": task,
            "timestamp": datetime.now().isoformat()
        })
        self.save_memory()

    def get_context(self) -> str:
        """Build context string from memory for LLM calls."""
        ctx = f"Agent: {self.name} ({self.role})\n"
        if self.memory["short_term"]:
            ctx += "Recent context:\n"
            for m in self.memory["short_term"][-5:]:
                ctx += f"- {m['key']}: {m['content']}\n"
        if self.memory["insights"]:
            ctx += "Insights:\n"
            for i in self.memory["insights"][-3:]:
                ctx += f"- {i['content']}\n"
        return ctx
