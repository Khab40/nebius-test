#!/usr/bin/env bash
set -euo pipefail
docker build -f app/Dockerfile -t repo-summarizer-api:local .
