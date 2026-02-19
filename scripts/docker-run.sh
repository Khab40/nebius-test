#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${NEBIUS_API_KEY:-}" ]]; then
  echo "NEBIUS_API_KEY is not set. Export it first:"
  echo '  export NEBIUS_API_KEY="..."'
  exit 1
fi

docker run --rm -p 8000:8000 \
  -e NEBIUS_API_KEY="$NEBIUS_API_KEY" \
  -e NEBIUS_MODEL="${NEBIUS_MODEL:-meta-llama/Meta-Llama-3.1-8B-Instruct-fast}" \
  -e NEBIUS_BASE_URL="${NEBIUS_BASE_URL:-https://api.tokenfactory.nebius.com/v1/}" \
  repo-summarizer-api:local
