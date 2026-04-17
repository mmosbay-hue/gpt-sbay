"""GitHub webhook → auto git pull + optional restart."""
import hmac
import hashlib
import os
import subprocess
import shlex
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/api/webhook", tags=["deploy"])

REPO_ROOT = Path(__file__).resolve().parent.parent
SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "").encode()
DEPLOY_BRANCH = os.getenv("DEPLOY_BRANCH", "main")
RESTART_CMD = os.getenv("DEPLOY_RESTART_CMD", "").strip()


def _verify(body: bytes, signature: str) -> bool:
    if not SECRET or not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=120
        )
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as e:
        return 1, str(e)


@router.post("/github")
async def github_webhook(request: Request):
    if not SECRET:
        raise HTTPException(500, "GITHUB_WEBHOOK_SECRET not configured")

    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not _verify(body, sig):
        raise HTTPException(401, "invalid signature")

    event = request.headers.get("X-GitHub-Event", "")
    if event == "ping":
        return {"ok": True, "pong": True}
    if event != "push":
        return {"ok": True, "skipped": event}

    payload = await request.json()
    ref = payload.get("ref", "")
    if ref != f"refs/heads/{DEPLOY_BRANCH}":
        return {"ok": True, "skipped": ref}

    steps = []
    for cmd in (
        ["git", "fetch", "--all"],
        ["git", "reset", "--hard", f"origin/{DEPLOY_BRANCH}"],
    ):
        code, out = _run(cmd, REPO_ROOT)
        steps.append({"cmd": " ".join(cmd), "code": code, "out": out[-400:]})
        if code != 0:
            raise HTTPException(500, {"failed_at": cmd, "log": steps})

    if RESTART_CMD:
        code, out = _run(shlex.split(RESTART_CMD), REPO_ROOT)
        steps.append({"cmd": RESTART_CMD, "code": code, "out": out[-400:]})

    return {"ok": True, "branch": DEPLOY_BRANCH, "steps": steps}
