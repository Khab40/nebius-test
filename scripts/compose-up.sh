#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${NEBIUS_API_KEY:-}" ]]; then
  echo "NEBIUS_API_KEY is not set. Export it first:"
  echo '  export NEBIUS_API_KEY="..."'
  exit 1
fi

docker compose up --build
