"""Dropbox backup — đẩy dữ liệu thư mục data/ lên Dropbox và giải phóng ổ đĩa server.

Cách hoạt động
--------------
- CSDL đang chạy (gptweb.db, conversations.db, knowledge/ChromaDB) được ZIP lại
  và upload lên Dropbox theo timestamp. KHÔNG xoá bản local vì app đang mở các
  file này liên tục — xoá là app hỏng.
- File người dùng upload trong data/uploads/ là thứ chiếm ổ đĩa nhiều nhất và có
  thể "giải phóng bộ nhớ trong": sau khi upload lên Dropbox, bản local cũ hơn
  UPLOAD_RETENTION_DAYS sẽ bị xoá. Link cũ vẫn hoạt động nhờ fallback tải lại từ
  Dropbox (xem fetch_upload_link()).

Cấu hình bằng biến môi trường (.env)
------------------------------------
- DROPBOX_REFRESH_TOKEN + DROPBOX_APP_KEY + DROPBOX_APP_SECRET  (khuyến nghị, token dài hạn)
  hoặc
- DROPBOX_ACCESS_TOKEN  (token ngắn hạn, sẽ hết hạn sau vài giờ)
- DROPBOX_BACKUP_DIR      (mặc định "/gpt-sbay-backups")
- BACKUP_KEEP             (số bản backup DB giữ lại trên Dropbox, mặc định 14)
- UPLOAD_RETENTION_DAYS   (giữ file upload local bao nhiêu ngày, mặc định 7; 0 = xoá hết sau khi backup)
"""
from __future__ import annotations

import io
import os
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
UPLOAD_DIR = DATA_DIR / "uploads"

BACKUP_DIR = os.getenv("DROPBOX_BACKUP_DIR", "/gpt-sbay-backups").rstrip("/") or "/gpt-sbay-backups"
BACKUP_KEEP = int(os.getenv("BACKUP_KEEP", "14"))
UPLOAD_RETENTION_DAYS = int(os.getenv("UPLOAD_RETENTION_DAYS", "7"))

# Ngưỡng dùng upload session (Dropbox giới hạn 150MB cho upload 1 phát)
_CHUNK = 8 * 1024 * 1024  # 8 MB
_SINGLE_SHOT_LIMIT = 140 * 1024 * 1024


class DropboxNotConfigured(RuntimeError):
    """Chưa cấu hình credential Dropbox."""


def is_configured() -> bool:
    if os.getenv("DROPBOX_ACCESS_TOKEN"):
        return True
    return bool(
        os.getenv("DROPBOX_REFRESH_TOKEN")
        and os.getenv("DROPBOX_APP_KEY")
        and os.getenv("DROPBOX_APP_SECRET")
    )


def get_client():
    """Tạo Dropbox client từ env. Ném DropboxNotConfigured nếu thiếu cấu hình."""
    try:
        import dropbox  # import lazy để app không crash nếu chưa cài lib
    except ImportError as e:  # pragma: no cover
        raise DropboxNotConfigured(
            "Chưa cài thư viện 'dropbox'. Chạy: pip install dropbox"
        ) from e

    refresh = os.getenv("DROPBOX_REFRESH_TOKEN")
    if refresh:
        return dropbox.Dropbox(
            oauth2_refresh_token=refresh,
            app_key=os.getenv("DROPBOX_APP_KEY"),
            app_secret=os.getenv("DROPBOX_APP_SECRET"),
            timeout=120,
        )

    token = os.getenv("DROPBOX_ACCESS_TOKEN")
    if token:
        return dropbox.Dropbox(token, timeout=120)

    raise DropboxNotConfigured(
        "Thiếu credential Dropbox. Cần DROPBOX_REFRESH_TOKEN + DROPBOX_APP_KEY + "
        "DROPBOX_APP_SECRET (hoặc DROPBOX_ACCESS_TOKEN)."
    )


def _upload_bytes(dbx, data: bytes, remote_path: str):
    """Upload dữ liệu bytes lên Dropbox, tự chọn single-shot hay session cho file lớn."""
    from dropbox.files import CommitInfo, UploadSessionCursor, WriteMode

    mode = WriteMode("overwrite")
    if len(data) <= _SINGLE_SHOT_LIMIT:
        dbx.files_upload(data, remote_path, mode=mode)
        return

    stream = io.BytesIO(data)
    first = stream.read(_CHUNK)
    session = dbx.files_upload_session_start(first)
    cursor = UploadSessionCursor(session_id=session.session_id, offset=stream.tell())
    commit = CommitInfo(path=remote_path, mode=mode)

    while True:
        chunk = stream.read(_CHUNK)
        if len(chunk) < _CHUNK:
            dbx.files_upload_session_finish(chunk, cursor, commit)
            break
        dbx.files_upload_session_append_v2(chunk, cursor)
        cursor.offset = stream.tell()


def _upload_file(dbx, local_path: Path, remote_path: str):
    _upload_bytes(dbx, local_path.read_bytes(), remote_path)


def _zip_databases() -> bytes:
    """ZIP các CSDL đang chạy + thư mục knowledge (ChromaDB) vào bộ nhớ."""
    buf = io.BytesIO()
    targets = [DATA_DIR / "gptweb.db", DATA_DIR / "conversations.db"]
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for db_file in targets:
            if db_file.exists():
                zf.write(db_file, arcname=db_file.name)
        knowledge = DATA_DIR / "knowledge"
        if knowledge.exists():
            for p in knowledge.rglob("*"):
                if p.is_file():
                    zf.write(p, arcname=str(p.relative_to(DATA_DIR)))
    return buf.getvalue()


def _prune_old_backups(dbx, keep: int):
    """Chỉ giữ lại `keep` bản backup DB mới nhất trên Dropbox."""
    from dropbox.exceptions import ApiError

    try:
        res = dbx.files_list_folder(BACKUP_DIR)
    except ApiError:
        return  # thư mục chưa tồn tại
    entries = [e for e in res.entries if e.name.startswith("data_") and e.name.endswith(".zip")]
    entries.sort(key=lambda e: e.name, reverse=True)
    for stale in entries[keep:]:
        try:
            dbx.files_delete_v2(stale.path_lower)
        except ApiError:
            pass


def backup_databases(dbx) -> dict:
    """ZIP + upload toàn bộ CSDL lên Dropbox. Trả về thông tin bản backup."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    remote = f"{BACKUP_DIR}/data_{ts}.zip"
    payload = _zip_databases()
    _upload_bytes(dbx, payload, remote)
    _prune_old_backups(dbx, BACKUP_KEEP)
    return {"remote_path": remote, "size_bytes": len(payload)}


def offload_uploads(dbx, retention_days: int) -> dict:
    """Đẩy file upload lên Dropbox rồi xoá bản local cũ để giải phóng ổ đĩa.

    File mới hơn retention_days vẫn giữ local (phục vụ nhanh). File cũ hơn: upload
    (nếu chưa có) rồi xoá local. Link /api/uploads/<name> vẫn chạy nhờ fallback.
    """
    if not UPLOAD_DIR.exists():
        return {"uploaded": 0, "freed_bytes": 0, "kept_local": 0}

    cutoff = time.time() - retention_days * 86400
    uploaded = freed = kept = 0

    for f in UPLOAD_DIR.iterdir():
        if not f.is_file():
            continue
        if f.stat().st_mtime > cutoff:
            kept += 1
            continue
        size = f.stat().st_size
        remote = f"{BACKUP_DIR}/uploads/{f.name}"
        try:
            _upload_file(dbx, f, remote)
            f.unlink()
            uploaded += 1
            freed += size
        except Exception:
            # Upload lỗi -> giữ nguyên bản local, không mất dữ liệu
            kept += 1

    return {"uploaded": uploaded, "freed_bytes": freed, "kept_local": kept}


def run_backup(free_space: bool = True) -> dict:
    """Điểm vào chính: backup DB, (tuỳ chọn) offload uploads. Trả về report."""
    if not is_configured():
        raise DropboxNotConfigured(
            "Chưa cấu hình Dropbox. Xem docs/DROPBOX_BACKUP.md để lấy token."
        )
    dbx = get_client()
    started = time.time()
    report = {
        "ok": True,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "databases": backup_databases(dbx),
        "uploads": None,
    }
    if free_space:
        report["uploads"] = offload_uploads(dbx, UPLOAD_RETENTION_DAYS)
    report["duration_sec"] = round(time.time() - started, 2)
    return report


def fetch_upload_link(name: str) -> str | None:
    """Trả về link tạm (temporary link) cho file upload đã offload lên Dropbox.

    Dùng cho fallback ở endpoint /api/uploads/<name> khi bản local đã bị xoá.
    Trả về None nếu chưa cấu hình Dropbox hoặc file không tồn tại trên Dropbox.
    """
    if not is_configured():
        return None
    try:
        from dropbox.exceptions import ApiError

        dbx = get_client()
        remote = f"{BACKUP_DIR}/uploads/{Path(name).name}"
        try:
            link = dbx.files_get_temporary_link(remote)
            return link.link
        except ApiError:
            return None
    except Exception:
        return None
