#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

: "${LLM_PROVIDER:=openai}"

if [[ "$LLM_PROVIDER" == "openai" ]]; then
  if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "OPENAI_API_KEY is not set. Export it first:"
    echo '  export OPENAI_API_KEY="..."'
    exit 1
  fi
elif [[ "$LLM_PROVIDER" == "nebius" ]]; then
  if [[ -z "${NEBIUS_API_KEY:-}" ]]; then
    echo "NEBIUS_API_KEY is not set. Export it first:"
    echo '  export NEBIUS_API_KEY="..."'
    exit 1
  fi
else
  echo 'LLM_PROVIDER must be "openai" or "nebius"'
  exit 1
fi

echo "Starting server on http://localhost:8000 (provider=$LLM_PROVIDER)"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
