"""DeepSeek AI — sinh code, phan tich, debug."""
import os
from pathlib import Path
from openai import OpenAI

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

_client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def ask(system: str, user: str, max_tokens: int = 2000) -> str:
    """Ask DeepSeek a question."""
    try:
        resp = _client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[ERROR] {e}"


def generate_code(task: str, current_code: str = "", max_tokens: int = 3000) -> str:
    """Generate or fix code."""
    return ask(
        system="""You are an expert frontend/backend developer.
Output ONLY the complete file content. No markdown fences. No explanations.
The code must be valid and runnable.""",
        user=f"Task: {task}\n\nCurrent code:\n{current_code}" if current_code else f"Task: {task}",
        max_tokens=max_tokens,
    )


def analyze(prompt: str, context: str = "", max_tokens: int = 800) -> str:
    """Analyze code/UI/bugs."""
    return ask(
        system="You are a senior code reviewer and UX analyst. Be specific and actionable.",
        user=f"{prompt}\n\n{context}" if context else prompt,
        max_tokens=max_tokens,
    )


def debug(error: str, code: str, max_tokens: int = 1500) -> str:
    """Debug and return fixed code."""
    return ask(
        system="""You are a debugging expert. Analyze the error, find root cause, and output the FIXED complete file.
Output ONLY code. No explanations. No markdown fences.""",
        user=f"Error:\n{error}\n\nCode:\n{code}",
        max_tokens=max_tokens,
    )
