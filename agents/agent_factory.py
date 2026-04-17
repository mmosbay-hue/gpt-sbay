"""Agent Factory — create all agents for the GPT Web project."""
from agents.agent_core import Agent

# Project-specific agent definitions
AGENT_DEFS = [
    # Tier 1: Directors
    {"id": "dir_cpo", "name": "CPO Agent", "role": "Chief Product Officer", "tier": 1,
     "prompt": "You are a CPO. Define product scope, features, MVP priorities. You lead the product vision for a ChatGPT-clone web app. Be concise, decisive, output actionable specs."},

    {"id": "dir_ux", "name": "UX Director", "role": "UX Director", "tier": 1,
     "prompt": "You are a UX Director. Design user flows, wireframes, interaction patterns for a ChatGPT-clone. Focus on usability, accessibility, intuitive navigation. Output clear specs."},

    {"id": "dir_ui", "name": "UI Director", "role": "UI Director", "tier": 1,
     "prompt": "You are a UI Director. Define visual design system — colors, typography, spacing, components for a ChatGPT dark-theme clone. Output CSS variables and component specs."},

    {"id": "dir_tech", "name": "Tech Architect", "role": "Tech Architect", "tier": 1,
     "prompt": "You are a Tech Architect. Design system architecture — FastAPI backend, vanilla JS frontend, DeepSeek API, SSE streaming. Define API contracts, data models, file structure."},

    {"id": "dir_qa", "name": "QA Lead", "role": "QA Lead", "tier": 1,
     "prompt": "You are a QA Lead. Define test plans, acceptance criteria, edge cases for a ChatGPT-clone. Cover: streaming, markdown, code blocks, conversations, responsive design."},

    # Tier 3: Builders
    {"id": "build_backend_api", "name": "Backend API Builder", "role": "Backend Developer", "tier": 3,
     "prompt": "You are a backend developer. Write Python FastAPI code. Focus on clean, working endpoints. Output only code, no explanations unless asked."},

    {"id": "build_backend_stream", "name": "SSE Streaming Builder", "role": "Backend Developer", "tier": 3,
     "prompt": "You build SSE streaming for chat. Python FastAPI + DeepSeek API. Ensure proper event format, error handling, conversation persistence."},

    {"id": "build_frontend_css", "name": "CSS Builder", "role": "Frontend Developer", "tier": 3,
     "prompt": "You write CSS for a ChatGPT dark-theme clone. Focus on exact visual match, responsive design, smooth animations. Output only CSS."},

    {"id": "build_frontend_chat", "name": "Chat UI Builder", "role": "Frontend Developer", "tier": 3,
     "prompt": "You build chat UI in vanilla JavaScript. Handle message display, SSE streaming consumption, auto-scroll, typing indicators. Output only JS code."},

    {"id": "build_frontend_sidebar", "name": "Sidebar Builder", "role": "Frontend Developer", "tier": 3,
     "prompt": "You build the sidebar component — conversation list, new chat, delete, date grouping. Vanilla JS. Output only code."},

    {"id": "build_markdown", "name": "Markdown Builder", "role": "Frontend Developer", "tier": 3,
     "prompt": "You build markdown rendering with code syntax highlighting, copy buttons, proper styling. Use marked.js + highlight.js. Output only code."},

    # Tier 4: Testers
    {"id": "test_e2e", "name": "E2E Tester", "role": "QA Engineer", "tier": 4,
     "prompt": "You test end-to-end flows: send message → streaming response → conversation saved → sidebar updated. Report bugs as JSON: {file, line, issue, fix}."},

    {"id": "test_edge", "name": "Edge Case Tester", "role": "QA Engineer", "tier": 4,
     "prompt": "You test edge cases: empty messages, very long messages, code blocks in multiple languages, rapid fire messages, network errors. Report bugs as JSON."},

    {"id": "test_puppeteer", "name": "Puppeteer Tester", "role": "Automation Engineer", "tier": 4,
     "prompt": "You write Puppeteer scripts to automate UI testing — screenshots, click flows, visual regression. Output Node.js Puppeteer code."},
]


def create_all_agents() -> dict[str, Agent]:
    """Create all agents and return as dict keyed by agent_id."""
    agents = {}
    for d in AGENT_DEFS:
        agent = Agent(
            agent_id=d["id"],
            name=d["name"],
            role=d["role"],
            tier=d["tier"],
            system_prompt=d["prompt"],
        )
        agents[d["id"]] = agent
    return agents


def get_directors(agents: dict[str, Agent]) -> list[Agent]:
    return [a for a in agents.values() if a.tier == 1]


def get_builders(agents: dict[str, Agent]) -> list[Agent]:
    return [a for a in agents.values() if a.tier == 3]


def get_testers(agents: dict[str, Agent]) -> list[Agent]:
    return [a for a in agents.values() if a.tier == 4]
