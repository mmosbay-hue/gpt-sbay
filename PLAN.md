# GPT Web — ChatGPT Clone Plan

## Tổng quan
Web chat UI/UX giống ChatGPT. 1% Claude chỉ huy, 99% DeepSeek + OpenClaw + Python + Puppeteer.

---

## Stack công nghệ

| Layer | Tech | Vai trò |
|-------|------|---------|
| Frontend | HTML/CSS/JS (vanilla) | ChatGPT-like UI, streaming responses |
| Backend | Python FastAPI | API server, SSE streaming, session management |
| LLM | DeepSeek API (OpenAI-compatible) | Xử lý chat, key: `sk-335a...dfc7` |
| Agent | OpenClaw 100 skills | Orchestrate agents, task delegation |
| Automation | Puppeteer (Node.js) | Web scraping, browser testing, screenshots |
| Message Bus | File-based JSON | Agent ↔ Agent 2-way communication |

### DeepSeek API
- Base URL: `https://api.deepseek.com`
- Model: `deepseek-chat` (rẻ, OpenAI SDK compatible)
- Dùng `openai` Python SDK, chỉ đổi `base_url`

---

## Kiến trúc Agent — 2 chiều, hiểu 100% trước khi code

### Phase 0: Agent Meeting (BẮT BUỘC trước khi code)
```
┌─────────────────────────────────────────────────┐
│              AGENT MEETING ROOM                  │
│                                                  │
│  Claude (CEO) → Đưa brief dự án                 │
│       ↓                                          │
│  5 Directors thảo luận 2 chiều:                  │
│    • CPO Agent: scope, features, MVP             │
│    • UX Director: user flow, wireframe           │
│    • UI Director: design system, components      │
│    • Tech Architect: stack, API design, DB       │
│    • QA Lead: test plan, acceptance criteria      │
│       ↓                                          │
│  Mỗi Director → assign tasks cho workers         │
│  Workers confirm hiểu → bắt đầu code            │
└─────────────────────────────────────────────────┘
```

### Quy trình 2 chiều
1. **Claude gửi brief** → tất cả agents nhận qua message bus
2. **Agents hỏi ngược** → nếu chưa hiểu, gửi câu hỏi về Claude
3. **Claude trả lời** → clarify cho đến khi 100% agents confirm
4. **Directors phân task** → workers nhận, confirm, bắt đầu
5. **Workers báo cáo** → progress, blockers, results → Directors → Claude

### Message Bus Protocol
```
message_bus/
  meeting_room/          # Phòng họp chung — tất cả agents đọc
  claude_inbox/          # Claude nhận báo cáo
  director_inbox/        # Directors nhận từ Claude + workers  
  worker_inbox/          # Workers nhận tasks từ Directors
```

---

## Cấu trúc dự án

```
GPT/
├── PLAN.md                    # File này
├── CLAUDE.md                  # Project instructions
├── requirements.txt           # Python deps
├── package.json               # Node deps (puppeteer, openclaw)
│
├── backend/                   # Python FastAPI
│   ├── main.py               # FastAPI app, CORS, routes
│   ├── config.py             # DeepSeek API config
│   ├── chat.py               # Chat endpoint + SSE streaming
│   ├── sessions.py           # Conversation history management
│   ├── models.py             # Pydantic models
│   └── deepseek_client.py    # DeepSeek API wrapper (OpenAI SDK)
│
├── frontend/                  # Static files
│   ├── index.html            # Main page
│   ├── css/
│   │   └── style.css         # ChatGPT-like styles (dark theme)
│   └── js/
│       ├── app.js            # Main app logic
│       ├── chat.js           # Chat UI + streaming
│       ├── sidebar.js        # Conversation list
│       └── markdown.js       # Markdown renderer
│
├── agents/                    # 100 Agent system
│   ├── agent_core.py         # Brain + Memory + Skills
│   ├── agent_factory.py      # Tạo 100 agents
│   ├── hierarchy.py          # Org chart
│   ├── pipeline.py           # 5-phase pipeline
│   ├── meeting.py            # Agent meeting room — 2-way discussion
│   ├── llm_router.py         # DeepSeek API rotation
│   └── memory_optimizer.py   # Dedup + compact
│
├── openclaw-skills/           # 100 skill files
│
├── message_bus/               # File-based messaging
│   ├── meeting_room/
│   ├── claude_inbox/
│   ├── director_inbox/
│   └── worker_inbox/
│
├── puppeteer/                 # Browser automation
│   ├── screenshot.js         # Chụp UI để review
│   ├── test_ui.js            # Auto test UI flows
│   └── scraper.js            # Scrape reference UIs
│
└── tests/                     # Test suite
    ├── test_chat.py
    ├── test_sessions.py
    └── test_agents.py
```

---

## UI/UX — Clone ChatGPT

### Layout
```
┌──────────────┬──────────────────────────────────┐
│  SIDEBAR     │          CHAT AREA               │
│              │                                    │
│ + New Chat   │  ┌────────────────────────────┐   │
│              │  │ User message (right align)  │   │
│ Today        │  └────────────────────────────┘   │
│  Chat 1      │  ┌────────────────────────────┐   │
│  Chat 2      │  │ AI response (left align)   │   │
│              │  │ with markdown rendering     │   │
│ Yesterday    │  │ code blocks + syntax hl     │   │
│  Chat 3      │  └────────────────────────────┘   │
│              │                                    │
│              │  ┌──────────────────────┬───────┐ │
│  Settings ⚙  │  │ Type a message...    │  ➤   │ │
│              │  └──────────────────────┴───────┘ │
└──────────────┴──────────────────────────────────┘
```

### Features MVP
1. **Dark theme** mặc định (giống ChatGPT)
2. **Streaming responses** (SSE — Server-Sent Events)
3. **Markdown rendering** (code blocks, tables, lists, bold/italic)
4. **Syntax highlighting** (highlight.js)
5. **Conversation history** — sidebar, grouped by date
6. **New chat** — tạo conversation mới
7. **Auto-scroll** — scroll xuống khi có response mới
8. **Copy code** — nút copy trên code blocks
9. **Responsive** — mobile friendly
10. **LocalStorage** — lưu conversations client-side

---

## Phân chia Agent Tasks (sau meeting)

### Phase 1: Setup (2 agents)
| Agent | Task |
|-------|------|
| Tech Architect | Setup FastAPI + DeepSeek client + config |
| Builder #1 | Setup frontend skeleton + dark theme CSS |

### Phase 2: Backend Core (5 agents)
| Agent | Task |
|-------|------|
| Builder #2 | `deepseek_client.py` — wrapper DeepSeek API |
| Builder #3 | `chat.py` — SSE streaming endpoint |
| Builder #4 | `sessions.py` — conversation CRUD |
| Builder #5 | `models.py` — Pydantic schemas |
| Builder #6 | `main.py` — FastAPI routes + CORS |

### Phase 3: Frontend Core (5 agents)
| Agent | Task |
|-------|------|
| UI Builder #1 | `style.css` — ChatGPT dark theme |
| UI Builder #2 | `chat.js` — message display + streaming |
| UI Builder #3 | `sidebar.js` — conversation list |
| UI Builder #4 | `markdown.js` — MD renderer + syntax hl |
| UI Builder #5 | `app.js` — orchestrate all modules |

### Phase 4: Integration + Test (3 agents)
| Agent | Task |
|-------|------|
| QA #1 | Test chat flow end-to-end |
| QA #2 | Test edge cases (empty, long, code blocks) |
| Puppeteer Agent | Screenshot UI + auto test clicks |

### Phase 5: Polish (2 agents)
| Agent | Task |
|-------|------|
| UX Agent | Review flow, fix UX issues |
| Perf Agent | Optimize loading, bundle size |

---

## API Endpoints

```
POST /api/chat              # Send message, receive SSE stream
GET  /api/conversations     # List all conversations
POST /api/conversations     # Create new conversation
GET  /api/conversations/:id # Get conversation messages
DEL  /api/conversations/:id # Delete conversation
```

---

## DeepSeek Config

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-335a777d92f34d7fa0ee170b1edddfc7",
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True
)
```

---

## Thứ tự thực thi

```
Step 1: Claude tạo project structure + install deps
Step 2: Agent Meeting — 5 Directors thảo luận, hiểu 100%
Step 3: Directors phân task → 17 workers
Step 4: Workers code song song (micro-tasks < 5 phút)
Step 5: Integration test + Puppeteer screenshot
Step 6: Polish + deploy
```

---

## Budget ước tính
- DeepSeek chat: ~$0.14/1M input, $0.28/1M output (rẻ hơn GPT-4o-mini)
- 100 agent calls × ~500 tokens = 50K tokens = ~$0.01
- Puppeteer: free (local)
- **Total: < $0.50 cho toàn bộ build**
