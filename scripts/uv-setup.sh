#!/usr/bin/env bash
set -euo pipefail

# Requires uv: https://astral.sh/uv
# Install: curl -Ls https://astral.sh/uv/install.sh | sh

uv python install 3.12
uv venv --python 3.12
uv pip install -r requirements.txt

echo "✅ Ready. Activate with:"
echo "  source .venv/bin/activate"
