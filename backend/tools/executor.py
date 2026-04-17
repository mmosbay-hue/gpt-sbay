"""Tool System — code execution, web browse, file processing."""
import subprocess
import sys
import os
import tempfile
import json


def execute_python(code: str, timeout: int = 10) -> dict:
    """Execute Python code safely in subprocess."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(code)
        f.flush()
        try:
            result = subprocess.run(
                [sys.executable, f.name],
                capture_output=True, text=True, timeout=timeout,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            return {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout[:2000],
                "stderr": result.stderr[:1000],
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "stderr": f"Execution timed out after {timeout}s"}
        finally:
            os.unlink(f.name)


def web_search_mock(query: str) -> dict:
    """Web search placeholder — returns mock results. In production: use real search API."""
    return {
        "status": "success",
        "results": [
            {"title": f"Result for: {query}", "snippet": "This is a placeholder. Connect a real search API (Google, Bing, SerpAPI) for live results."},
        ]
    }


def process_file(filepath: str) -> str:
    """Read and extract text from uploaded file."""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext in ('.txt', '.py', '.js', '.html', '.css', '.json', '.csv', '.md'):
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()[:10000]
        elif ext == '.pdf':
            # Basic PDF text extraction
            try:
                import PyPDF2
                with open(filepath, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages[:20]:
                        text += page.extract_text() + "\n"
                    return text[:10000]
            except ImportError:
                return f"[PDF file: {os.path.basename(filepath)} - install PyPDF2 for text extraction]"
        else:
            return f"[File: {os.path.basename(filepath)} ({ext})]"
    except Exception as e:
        return f"[Error reading file: {e}]"


TOOL_REGISTRY = {
    "code_exec": {
        "name": "Code Interpreter",
        "description": "Execute Python code",
        "handler": execute_python,
    },
    "web_browse": {
        "name": "Web Browsing",
        "description": "Search the web",
        "handler": web_search_mock,
    },
    "file_upload": {
        "name": "File Upload",
        "description": "Upload and process files",
        "handler": process_file,
    },
}
