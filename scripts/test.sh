#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://localhost:8000/summarize}"
REPO="${2:-https://github.com/psf/requests}"

curl -sS -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "{"github_url": "${REPO}"}" | python -m json.tool
