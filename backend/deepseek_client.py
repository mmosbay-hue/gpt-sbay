"""DeepSeek API client — OpenAI SDK compatible."""
from openai import OpenAI
from backend.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# Cac model duoc ho tro — alias map cho UI label
SUPPORTED_MODELS = {
    "deepseek-chat": "deepseek-chat",
    "deepseek-reasoner": "deepseek-reasoner",
    # UI label aliases
    "ChatGPT": "deepseek-chat",
    "DeepSeek": "deepseek-chat",
    "DeepSeek Reasoner": "deepseek-reasoner",
    "GPT-4o-mini": "deepseek-chat",  # fallback - khong co OpenAI key thuc su
}


def resolve_model(name: str | None) -> str:
    """Map UI model name -> actual API model id."""
    if not name:
        return DEEPSEEK_MODEL
    return SUPPORTED_MODELS.get(name, DEEPSEEK_MODEL)


def chat(messages: list[dict], stream: bool = True, model: str | None = None):
    """Send chat request to DeepSeek. Returns stream or completion."""
    actual_model = resolve_model(model)
    return client.chat.completions.create(
        model=actual_model,
        messages=messages,
        stream=stream,
        temperature=0.7,
        max_tokens=4096,
    )


def chat_sync(messages: list[dict]) -> str:
    """Non-streaming chat — returns full response text."""
    resp = chat(messages, stream=False)
    return resp.choices[0].message.content
