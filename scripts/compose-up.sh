#!/usr/bin/env bash
set -euo pipefail

: "${LLM_PROVIDER:=openai}"

if [[ "$LLM_PROVIDER" == "openai" && -z "${OPENAI_API_KEY:-}" ]]; then
  echo "OPENAI_API_KEY is not set. Export it first:"
  echo '  export OPENAI_API_KEY="..."'
  exit 1
fi

if [[ "$LLM_PROVIDER" == "nebius" && -z "${NEBIUS_API_KEY:-}" ]]; then
  echo "NEBIUS_API_KEY is not set. Export it first:"
  echo '  export NEBIUS_API_KEY="..."'
  exit 1
fi

docker compose up --build
