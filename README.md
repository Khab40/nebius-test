# Repo Summarizer API (FastAPI)

API service that accepts a public GitHub repository URL and returns:
- a human-readable summary
- main technologies used
- brief project structure description

It downloads the repo as a ZIP, filters/chooses the most relevant files (README/docs/configs/tree + selected code),
fits them into the LLM context window, and calls an LLM to generate the summary.

## Requirements
- Python 3.10+

## LLM providers
Supports **OpenAI by default**, and **Nebius Token Factory** optionally.

### OpenAI (default)
Env vars:
- `OPENAI_API_KEY` (required)
- `OPENAI_MODEL` (optional, default: `gpt-4o-mini`)
- `OPENAI_BASE_URL` (optional, default: `https://api.openai.com/v1/`)
- `LLM_PROVIDER` (optional, default: `openai`)

### Nebius Token Factory (optional)
Env vars:
- `NEBIUS_API_KEY` (required)
- `NEBIUS_MODEL` (optional, default: `meta-llama/Meta-Llama-3.1-8B-Instruct-fast`)
- `NEBIUS_BASE_URL` (optional, default: `https://api.tokenfactory.nebius.com/v1/`)
- `LLM_PROVIDER=nebius`

## Install (local dev, no Docker)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run locally (OpenAI)
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY="YOUR_OPENAI_KEY"
# Optional:
export OPENAI_MODEL="gpt-4o-mini"

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Run locally (Nebius)
```bash
export LLM_PROVIDER=nebius
export NEBIUS_API_KEY="YOUR_NEBIUS_KEY"
# Optional:
export NEBIUS_MODEL="meta-llama/Meta-Llama-3.1-8B-Instruct-fast"

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Test
```bash
curl -X POST http://localhost:8000/summarize   -H "Content-Type: application/json"   -d '{"github_url": "https://github.com/psf/requests"}'
```

## Docker (optional)
```bash
# OpenAI:
export OPENAI_API_KEY="YOUR_OPENAI_KEY"
docker compose up --build
```

## Error format
On error:
```json
{ "status": "error", "message": "..." }
```

## Repo→LLM strategy (what we send)
1) Directory tree (depth-limited; ignores node_modules, dist, venv, binaries, etc.)
2) README + key docs
3) Dependency/config files
4) Endpoint-ish / entrypoint / main modules
5) Strict truncation budget to fit context window


## Answers on submission questions (Khab40)
### Q: Which model you chose and why?
### A: I chose gpt-4o-mini for Open AI and meta-llama/Meta-Llama-3.1-8B-Instruct-fast for Nebius because of the wish to keep balance between quality, speed and cost.

### Q: Your approach to handling repository contents
### A: Exclude binaries, build artifacts, generated data; take folders tree, documents, API end-points, etc. Can be improved with chunks, RAG but decided to make it simple and fast to supply to Nebius. 