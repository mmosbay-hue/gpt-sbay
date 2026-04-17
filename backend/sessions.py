"""Conversation session management — SQLite persistent storage."""
import uuid
import json
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "conversations.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_table():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT 'New Chat',
            messages TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


_init_table()


def _row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "messages": json.loads(row["messages"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_conversation(title: str | None = None) -> dict:
    conv_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    conn = _get_conn()
    conn.execute(
        "INSERT INTO conversations (id, title, messages, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (conv_id, title or "New Chat", "[]", now, now)
    )
    conn.commit()
    conn.close()
    return {"id": conv_id, "title": title or "New Chat", "messages": [], "created_at": now, "updated_at": now}


def get_conversation(conv_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def list_conversations() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT 100").fetchall()
    conn.close()
    return [{"id": r["id"], "title": r["title"], "created_at": r["created_at"], "updated_at": r["updated_at"]} for r in rows]


def add_message(conv_id: str, role: str, content: str) -> dict | None:
    conv = get_conversation(conv_id)
    if not conv:
        return None

    msgs = conv["messages"]
    msgs.append({"role": role, "content": content})

    # Keep last 200
    if len(msgs) > 200:
        msgs = msgs[-200:]

    now = datetime.now().isoformat()
    title = conv["title"]

    # Auto-title from first user message
    if title == "New Chat" and role == "user":
        title = content[:50] + ("..." if len(content) > 50 else "")

    conn = _get_conn()
    conn.execute(
        "UPDATE conversations SET messages = ?, title = ?, updated_at = ? WHERE id = ?",
        (json.dumps(msgs, ensure_ascii=False), title, now, conv_id)
    )
    conn.commit()
    conn.close()

    conv["messages"] = msgs
    conv["title"] = title
    conv["updated_at"] = now
    return conv


def delete_conversation(conv_id: str) -> bool:
    conn = _get_conn()
    cursor = conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def search_conversations(query: str) -> list[dict]:
    """Search conversations by title or message content."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE title LIKE ? OR messages LIKE ? ORDER BY updated_at DESC LIMIT 20",
        (f"%{query}%", f"%{query}%")
    ).fetchall()
    conn.close()
    return [{"id": r["id"], "title": r["title"], "created_at": r["created_at"], "updated_at": r["updated_at"]} for r in rows]


def export_conversations() -> dict:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM conversations ORDER BY updated_at DESC").fetchall()
    conn.close()
    return {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "conversations": [_row_to_dict(r) for r in rows]
    }


def import_conversations(data: dict) -> dict:
    if not isinstance(data, dict):
        return {"success": False, "message": "Invalid data format"}

    conversations = data.get("conversations", [])
    if not isinstance(conversations, list):
        return {"success": False, "message": "Conversations must be a list"}

    imported = 0
    skipped = 0
    errors = 0
    conn = _get_conn()

    for conv in conversations:
        if not isinstance(conv, dict):
            errors += 1
            continue

        conv_id = conv.get("id")
        if not conv_id:
            errors += 1
            continue

        existing = conn.execute("SELECT id FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        if existing:
            skipped += 1
            continue

        try:
            conn.execute(
                "INSERT INTO conversations (id, title, messages, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (conv_id, conv.get("title", "Imported"), json.dumps(conv.get("messages", []), ensure_ascii=False),
                 conv.get("created_at", datetime.now().isoformat()), conv.get("updated_at", datetime.now().isoformat()))
            )
            imported += 1
        except Exception:
            errors += 1

    conn.commit()
    conn.close()
    return {"success": True, "imported": imported, "skipped": skipped, "errors": errors}
