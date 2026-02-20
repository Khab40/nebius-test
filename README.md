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
- `OPENAI_EMBEDDING_MODEL` (optional, default: `text-embedding-3-small`)
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
pip install -r app/requirements.txt
```

## Run locally (OpenAI)
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY="YOUR_OPENAI_KEY"
# Optional:
export OPENAI_MODEL="gpt-4o-mini"
export OPENAI_EMBEDDING_MODEL="text-embedding-3-small"

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

# Or build the API image directly:
docker build -f app/Dockerfile -t repo-summarizer-api:local .
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
4) Deterministic extraction: dependencies + entrypoints + detected endpoints
5) RAG-selected code chunks: chunk selected important files and retrieve top relevant chunks for: what it does / how to run / endpoints / structure / deps


## Answers on submission questions (Khab40)
Q: Which model you chose and why?
A: I chose gpt-4o-mini for Open AI and meta-llama/Meta-Llama-3.1-8B-Instruct-fast for Nebius because of the wish to keep balance between quality, speed and cost.

Q: Your approach to handling repository contents
A: Exclude binaries/build artifacts/generated data; include directory tree + docs + dependency/config files; extract endpoints/entrypoints deterministically; then use RAG-selected top-K chunks (chunk important files and retrieve the most relevant snippets) to fit the LLM context window while keeping high signal.
