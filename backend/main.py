"""FastAPI main app — SbayAI SaaS."""
import os
import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.chat import router as chat_router
from backend.auth.routes import router as auth_router
from backend.billing.routes import router as billing_router
from backend.admin.routes import router as admin_router
from backend.gpts.routes import router as gpts_router
from backend.affiliate.routes import router as affiliate_router
from backend.sessions import (
    list_conversations, get_conversation, delete_conversation,
    create_conversation, export_conversations, import_conversations,
    search_conversations,
)
from backend.models import ConversationCreate
from backend.db.database import init_db
from backend.config import HOST, PORT

app = FastAPI(title="SbayAI SaaS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Routers
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(admin_router)
app.include_router(gpts_router)
app.include_router(affiliate_router)


# ============ Conversation API ============
@app.get("/api/conversations")
async def api_list_conversations():
    return list_conversations()


@app.post("/api/conversations")
async def api_create_conversation(req: ConversationCreate):
    return create_conversation(req.title)


@app.get("/api/conversations/{conv_id}")
async def api_get_conversation(conv_id: str):
    conv = get_conversation(conv_id)
    if not conv:
        return {"error": "not found"}
    return conv


@app.delete("/api/conversations/{conv_id}")
async def api_delete_conversation(conv_id: str):
    deleted = delete_conversation(conv_id)
    return {"deleted": deleted}


@app.post("/api/conversations/{conv_id}/rename")
async def api_rename_conversation(conv_id: str, title: str = ""):
    if not title.strip():
        return {"error": "Title required"}
    from backend.sessions import _get_conn
    conn = _get_conn()
    conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (title.strip(), conv_id))
    conn.commit()
    conn.close()
    return {"renamed": True, "title": title.strip()}


@app.get("/api/search")
async def api_search(q: str = ""):
    if not q.strip():
        return []
    return search_conversations(q)


@app.post("/api/leads")
async def api_collect_lead(data: dict):
    """Thu thập email leads từ landing page."""
    email = data.get("email", "").strip()
    if not email or "@" not in email:
        return {"error": "Invalid email"}
    import sqlite3
    conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent / "data" / "gptweb.db"))
    conn.execute("CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY, email TEXT UNIQUE, created_at TEXT)")
    try:
        from datetime import datetime
        conn.execute("INSERT OR IGNORE INTO leads (email, created_at) VALUES (?, ?)", (email, datetime.now().isoformat()))
        conn.commit()
    except Exception:
        pass
    conn.close()
    return {"ok": True}


@app.get("/api/export")
async def api_export():
    return export_conversations()


# ============ File Upload ============
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".txt", ".md", ".csv",
               ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".json", ".html", ".js", ".py", ".java", ".c", ".cpp"}


@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)):
    """Upload file dinh kem chat. Tra ve URL + content (neu text)."""
    # Validate ext
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Loai file khong ho tro: {ext}")

    # Read & validate size
    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail=f"File qua lon (>{MAX_UPLOAD_SIZE//1024//1024}MB)")

    # Save with unique name
    file_id = uuid.uuid4().hex[:12]
    safe_name = f"{file_id}{ext}"
    file_path = UPLOAD_DIR / safe_name
    file_path.write_bytes(data)

    is_image = ext in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    is_text = ext in {".txt", ".md", ".csv", ".json", ".html", ".js", ".py", ".java", ".c", ".cpp"}

    # Trich noi dung neu la text (max 10k chars de gui kem prompt)
    text_content = None
    if is_text:
        try:
            text_content = data.decode("utf-8", errors="replace")[:10000]
        except Exception:
            text_content = None

    return {
        "id": file_id,
        "name": file.filename,
        "url": f"/api/uploads/{safe_name}",
        "size": len(data),
        "type": file.content_type or "application/octet-stream",
        "is_image": is_image,
        "is_text": is_text,
        "text_content": text_content,
    }


@app.get("/api/uploads/{name}")
async def api_get_upload(name: str):
    """Phuc vu file upload."""
    # Chong path traversal
    safe = Path(name).name  # strip path components
    fp = UPLOAD_DIR / safe
    if not fp.exists() or not fp.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(fp))


@app.get("/api/tts")
async def api_tts(text: str = ""):
    """Text-to-Speech — Vbee (giọng Trình) hoặc fallback Google TTS."""
    if not text.strip():
        return {"error": "No text"}

    import io
    import asyncio
    import httpx
    from fastapi.responses import StreamingResponse as SR
    from backend.config import VBEE_TOKEN, VBEE_APP_ID, VBEE_VOICE_CODE

    # === Vbee TTS ===
    if VBEE_TOKEN and VBEE_APP_ID:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Step 1: POST tạo TTS request
                resp = await client.post(
                    "https://vbee.vn/api/v1/tts",
                    headers={
                        "Authorization": f"Bearer {VBEE_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "app_id": VBEE_APP_ID,
                        "input_text": text[:1000],
                        "voice_code": VBEE_VOICE_CODE,
                        "audio_type": "mp3",
                        "bitrate": 128,
                        "speed_rate": "1.0",
                    },
                )

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == 1:
                        request_id = data["result"]["request_id"]

                        # Step 2: Poll GET cho đến khi SUCCESS (max 15s)
                        for _ in range(30):
                            await asyncio.sleep(0.5)
                            poll = await client.get(
                                f"https://vbee.vn/api/v1/tts/{request_id}",
                                headers={"Authorization": f"Bearer {VBEE_TOKEN}"},
                            )
                            if poll.status_code == 200:
                                poll_data = poll.json()
                                result = poll_data.get("result", {})
                                if result.get("status") == "SUCCESS" and result.get("audio_link"):
                                    # Step 3: Download audio
                                    audio_resp = await client.get(result["audio_link"])
                                    if audio_resp.status_code == 200:
                                        return SR(io.BytesIO(audio_resp.content), media_type="audio/mpeg")
                                    break
                                elif result.get("status") == "FAILURE":
                                    break
        except Exception as e:
            print(f"Vbee TTS error: {e}")

    # === Fallback: Google TTS ===
    from gtts import gTTS
    tts = gTTS(text=text[:500], lang='vi', slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return SR(buf, media_type="audio/mpeg")


@app.get("/api/conversations/{conv_id}/markdown")
async def api_export_markdown(conv_id: str):
    conv = get_conversation(conv_id)
    if not conv:
        return {"error": "not found"}
    md = f"# {conv['title']}\n\n"
    for msg in conv["messages"]:
        role = "**You**" if msg["role"] == "user" else "**SbayAI**"
        md += f"{role}:\n{msg['content']}\n\n---\n\n"
    return {"markdown": md, "title": conv["title"]}


@app.post("/api/import")
async def api_import(data: dict):
    return import_conversations(data)


# ============ Page Routes ============
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def landing_page():
    return FileResponse("frontend/landing/index.html")


@app.get("/chat")
async def chat_page():
    return FileResponse("frontend/index.html")


@app.get("/login")
async def login_page():
    return FileResponse("frontend/landing/login.html")


@app.get("/register")
async def register_page():
    return FileResponse("frontend/landing/register.html")


@app.get("/pricing")
async def pricing_page():
    return FileResponse("frontend/landing/pricing.html")


@app.get("/dashboard")
async def user_dashboard():
    return FileResponse("frontend/dashboard/index.html")


@app.get("/admin")
async def admin_dashboard():
    return FileResponse("frontend/admin/index.html")


@app.get("/affiliate")
async def affiliate_page():
    return FileResponse("frontend/affiliate/index.html")


@app.get("/guide")
async def guide_page():
    return FileResponse("frontend/guide/index.html")


@app.get("/gpt-builder")
async def gpt_builder_page():
    return FileResponse("frontend/gpt-builder/index.html")


@app.get("/sw.js")
async def service_worker():
    return FileResponse("frontend/sw.js", media_type="application/javascript")


@app.get("/robots.txt")
async def robots():
    return FileResponse("frontend/robots.txt", media_type="text/plain")


@app.get("/sitemap.xml")
async def sitemap():
    return FileResponse("frontend/sitemap.xml", media_type="application/xml")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
