#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "Starting server on http://localhost:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
