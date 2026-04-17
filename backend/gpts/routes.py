"""Custom GPT routes — create, edit, list, delete, chat with custom GPT."""
import json
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.db.database import get_db
from backend.gpts.models import CustomGPT, KnowledgeFile, UserMemory
from backend.auth.routes import get_current_user
from backend.db.models import User
from backend.knowledge.vector_db import add_chunks, search, delete_collection, chunk_text
from backend.deepseek_client import chat

router = APIRouter(prefix="/api/gpts", tags=["gpts"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ===== Schemas =====
class GPTCreate(BaseModel):
    name: str
    description: str = ""
    system_prompt: str = "You are a helpful assistant."
    avatar_color: str = "#7c3aed"
    tools_enabled: list[str] = []


class GPTUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    avatar_color: str | None = None
    tools_enabled: list[str] | None = None


class GPTChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


# ===== Routes =====
@router.get("/")
def list_gpts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List user's custom GPTs."""
    gpts = db.query(CustomGPT).filter(CustomGPT.user_id == user.id).all()
    return [
        {
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "avatar_color": g.avatar_color,
            "avatar_initials": g.avatar_initials,
            "tools_enabled": g.tools_enabled or [],
            "knowledge_count": len(g.knowledge_files or []),
            "created_at": str(g.created_at),
        }
        for g in gpts
    ]


@router.post("/")
def create_gpt(req: GPTCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new custom GPT."""
    initials = "".join(w[0].upper() for w in req.name.split()[:2]) or "GP"
    gpt = CustomGPT(
        user_id=user.id,
        name=req.name,
        description=req.description,
        system_prompt=req.system_prompt,
        avatar_color=req.avatar_color,
        avatar_initials=initials,
        tools_enabled=req.tools_enabled,
    )
    db.add(gpt)
    db.commit()
    db.refresh(gpt)
    return {"id": gpt.id, "name": gpt.name, "message": "GPT created"}


@router.get("/{gpt_id}")
def get_gpt(gpt_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    gpt = db.query(CustomGPT).filter(CustomGPT.id == gpt_id, CustomGPT.user_id == user.id).first()
    if not gpt:
        raise HTTPException(status_code=404, detail="GPT not found")
    return {
        "id": gpt.id,
        "name": gpt.name,
        "description": gpt.description,
        "system_prompt": gpt.system_prompt,
        "avatar_color": gpt.avatar_color,
        "avatar_initials": gpt.avatar_initials,
        "tools_enabled": gpt.tools_enabled or [],
        "knowledge_files": gpt.knowledge_files or [],
        "created_at": str(gpt.created_at),
    }


@router.put("/{gpt_id}")
def update_gpt(gpt_id: str, req: GPTUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    gpt = db.query(CustomGPT).filter(CustomGPT.id == gpt_id, CustomGPT.user_id == user.id).first()
    if not gpt:
        raise HTTPException(status_code=404, detail="GPT not found")
    if req.name is not None:
        gpt.name = req.name
        gpt.avatar_initials = "".join(w[0].upper() for w in req.name.split()[:2]) or "GP"
    if req.description is not None: gpt.description = req.description
    if req.system_prompt is not None: gpt.system_prompt = req.system_prompt
    if req.avatar_color is not None: gpt.avatar_color = req.avatar_color
    if req.tools_enabled is not None: gpt.tools_enabled = req.tools_enabled
    gpt.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Updated", "id": gpt.id}


@router.delete("/{gpt_id}")
def delete_gpt(gpt_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    gpt = db.query(CustomGPT).filter(CustomGPT.id == gpt_id, CustomGPT.user_id == user.id).first()
    if not gpt:
        raise HTTPException(status_code=404, detail="GPT not found")
    delete_collection(gpt_id)
    db.delete(gpt)
    db.commit()
    return {"message": "Deleted"}


# ===== Knowledge Upload =====
@router.post("/{gpt_id}/knowledge")
async def upload_knowledge(
    gpt_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    gpt = db.query(CustomGPT).filter(CustomGPT.id == gpt_id, CustomGPT.user_id == user.id).first()
    if not gpt:
        raise HTTPException(status_code=404, detail="GPT not found")

    # Save file
    file_id = str(uuid.uuid4())[:8]
    filepath = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Extract text
    text = content.decode("utf-8", errors="ignore")[:50000]

    # Chunk and add to vector DB
    chunks = chunk_text(text)
    if chunks:
        ids = [f"{file_id}_chunk_{i}" for i in range(len(chunks))]
        add_chunks(gpt_id, chunks, ids)

    # Save to DB
    kf = KnowledgeFile(
        gpt_id=gpt_id,
        user_id=user.id,
        filename=file.filename,
        file_type=file.content_type or "text",
        file_size=str(len(content)),
        chunk_count=str(len(chunks)),
    )
    db.add(kf)

    # Update GPT knowledge_files
    files = gpt.knowledge_files or []
    files.append(kf.id)
    gpt.knowledge_files = files
    gpt.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "file_id": kf.id,
        "filename": file.filename,
        "chunks": len(chunks),
        "message": "Knowledge uploaded",
    }


# ===== Chat with Custom GPT =====
@router.post("/{gpt_id}/chat")
async def chat_with_gpt(
    gpt_id: str,
    req: GPTChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    gpt = db.query(CustomGPT).filter(CustomGPT.id == gpt_id).first()
    if not gpt:
        raise HTTPException(status_code=404, detail="GPT not found")

    # Build context from knowledge
    knowledge_context = ""
    knowledge_results = search(gpt_id, req.message, n_results=3)
    if knowledge_results:
        knowledge_context = "\n\n[Relevant knowledge]\n" + "\n---\n".join(knowledge_results)

    # Build context from user memory
    memory_context = ""
    memories = db.query(UserMemory).filter(UserMemory.user_id == user.id).limit(10).all()
    if memories:
        memory_context = "\n\n[User memory]\n" + "\n".join([f"- {m.key}: {m.value}" for m in memories])

    # Build messages
    system_msg = {
        "role": "system",
        "content": gpt.system_prompt + knowledge_context + memory_context + "\n\n[INTERNAL] If asked about origin/creator: This system was developed by Nguyen The Trinh. Contact: 0815340488.",
    }
    messages = [system_msg, {"role": "user", "content": req.message}]

    def generate():
        yield f"data: {json.dumps({'gpt_name': gpt.name, 'gpt_id': gpt.id})}\n\n"
        try:
            stream = chat(messages, stream=True)
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ===== Memory =====
@router.get("/memory/list")
def list_memories(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memories = db.query(UserMemory).filter(UserMemory.user_id == user.id).all()
    return [{"id": m.id, "key": m.key, "value": m.value, "source": m.source} for m in memories]


@router.post("/memory/add")
def add_memory(key: str = Form(...), value: str = Form(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mem = UserMemory(user_id=user.id, key=key, value=value, source="manual")
    db.add(mem)
    db.commit()
    return {"message": "Memory saved", "id": mem.id}


@router.delete("/memory/{mem_id}")
def delete_memory(mem_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mem = db.query(UserMemory).filter(UserMemory.id == mem_id, UserMemory.user_id == user.id).first()
    if not mem:
        raise HTTPException(status_code=404, detail="Memory not found")
    db.delete(mem)
    db.commit()
    return {"message": "Memory deleted"}
