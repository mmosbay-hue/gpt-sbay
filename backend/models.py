"""Pydantic models."""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    model: str | None = None  # vd: "deepseek-chat", "deepseek-reasoner"
    system_prompt: str | None = None  # tuy chinh system prompt theo preset GPT
    temporary: bool = False  # True = không lưu, không dùng history


class ConversationCreate(BaseModel):
    title: str | None = None


class Message(BaseModel):
    role: str  # user | assistant
    content: str


class Conversation(BaseModel):
    id: str
    title: str
    messages: list[Message] = []
    created_at: str
    updated_at: str
