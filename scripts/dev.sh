#!/usr/bin/env bash
set -euo pipefail

# Requires uv: https://astral.sh/uv
# Install: curl -Ls https://astral.sh/uv/install.sh | sh

: "${LLM_PROVIDER:=openai}"

if [[ "$LLM_PROVIDER" == "openai" ]]; then
  if [[ -z "${OPENAI_API_KEY:-}" && ! -f .env ]]; then
    echo "OPENAI_API_KEY is not set and .env not found. Either:"
    echo '  export OPENAI_API_KEY="..."'
    echo "or create .env (see .env.example)"
    exit 1
  fi
elif [[ "$LLM_PROVIDER" == "nebius" ]]; then
  if [[ -z "${NEBIUS_API_KEY:-}" && ! -f .env ]]; then
    echo "NEBIUS_API_KEY is not set and .env not found. Either:"
    echo '  export NEBIUS_API_KEY="..."'
    echo "or create .env (see .env.example)"
    exit 1
  fi
else
  echo 'LLM_PROVIDER must be "openai" or "nebius"'
  exit 1
fi

uv python install 3.12
uv venv --python 3.12
uv pip install -r app/requirements.txt

source .venv/bin/activate

echo "Starting server on http://localhost:8000 (provider=$LLM_PROVIDER)"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
