"""Custom GPT database models."""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.db.database import Base
import uuid


def gen_id():
    return str(uuid.uuid4())[:12]


class CustomGPT(Base):
    __tablename__ = "custom_gpts"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    avatar_color = Column(String, default="#7c3aed")
    avatar_initials = Column(String, default="GP")
    system_prompt = Column(Text, default="You are a helpful assistant.")
    tools_enabled = Column(JSON, default=list)  # ["web_browse", "code_exec", "file_upload"]
    knowledge_files = Column(JSON, default=list)  # ["file_id_1", "file_id_2"]
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class KnowledgeFile(Base):
    __tablename__ = "knowledge_files"

    id = Column(String, primary_key=True, default=gen_id)
    gpt_id = Column(String, ForeignKey("custom_gpts.id"), nullable=False)
    user_id = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, default="text")  # text, pdf, csv
    file_size = Column(String, default="0")
    chunk_count = Column(String, default="0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class UserMemory(Base):
    __tablename__ = "user_memories"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    key = Column(String, nullable=False)
    value = Column(Text, nullable=False)
    source = Column(String, default="auto")  # auto | manual
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
