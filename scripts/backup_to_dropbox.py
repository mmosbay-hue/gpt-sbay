#!/usr/bin/env python3
"""CLI backup lên Dropbox — dùng cho cron.

Ví dụ crontab (backup + giải phóng ổ đĩa mỗi ngày lúc 3h sáng):
    0 3 * * * cd /www/python/gpt-sbay && /www/python/gpt-sbay/venv/bin/python scripts/backup_to_dropbox.py >> data/backup.log 2>&1

Chạy tay:
    python scripts/backup_to_dropbox.py            # backup + offload uploads
    python scripts/backup_to_dropbox.py --no-free  # chỉ backup, không xoá local
"""
import json
import os
import sys

# Cho phép chạy từ thư mục gốc dự án
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Nạp .env nếu có (không phụ thuộc python-dotenv)
_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.isfile(_env):
    with open(_env, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from backend.dropbox_backup import DropboxNotConfigured, run_backup  # noqa: E402


def main() -> int:
    free_space = "--no-free" not in sys.argv
    try:
        report = run_backup(free_space=free_space)
    except DropboxNotConfigured as e:
        print(f"[backup] CHƯA CẤU HÌNH DROPBOX: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"[backup] LỖI: {e}", file=sys.stderr)
        return 1

    print("[backup] OK " + json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
