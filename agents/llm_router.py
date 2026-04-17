"""LLM Router — DeepSeek API for all agent calls."""
from openai import OpenAI

DEEPSEEK_KEY = "sk-335a777d92f34d7fa0ee170b1edddfc7"
DEEPSEEK_URL = "https://api.deepseek.com"

_client = OpenAI(api_key=DEEPSEEK_KEY, base_url=DEEPSEEK_URL)


def call_agent(system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
    """Call DeepSeek for an agent response."""
    try:
        resp = _client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[ERROR] {e}"


def call_agent_with_history(messages: list[dict], max_tokens: int = 500) -> str:
    """Call DeepSeek with full message history (for multi-turn agent discussions)."""
    try:
        resp = _client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[ERROR] {e}"
