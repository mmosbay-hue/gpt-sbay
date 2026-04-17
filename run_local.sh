#!/usr/bin/env bash
# Script chạy SbayAI ở local (Git Bash trên Windows)
set -e

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
  echo ">>> Tạo virtualenv..."
  python -m venv venv
fi

source venv/Scripts/activate 2>/dev/null || source venv/bin/activate

echo ">>> Cài dependencies..."
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
  echo ">>> Chưa có .env — copy từ .env.example"
  cp .env.example .env
  echo "!!! Hãy mở file .env và điền DEEPSEEK_API_KEY trước khi chạy lại"
  exit 1
fi

echo ">>> Khởi động server tại http://localhost:8080"
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8080
