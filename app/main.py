import os
import json
import logging
from datetime import datetime, timezone

# Load .env only for local development.
# Set ENV=prod (or anything other than "dev") to disable.
if os.getenv("ENV", "dev").lower() == "dev":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        # dotenv is optional in production; if missing, rely on real env vars.
        pass
    

# --- Structured JSON logging setup ---

class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter for container-friendly logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper().strip()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers in reload mode
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)


setup_logging()
logger = logging.getLogger(__name__)
logger.info("Starting Repo Summarizer API")
    
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .schemas import SummarizeRequest, SummarizeResponse, ErrorResponse
from .github import (
    parse_github_repo_url,
    assert_repo_accessible,
    download_repo_zip,
    extract_zip_to_tempdir,
    GitHubBadUrl,
    GitHubNotFound,
    GitHubPrivateOrForbidden,
    GitHubRateLimited,
    GitHubError,
)
from .summarize import summarize_repo, SummarizationError


app = FastAPI(title="Repo Summarizer API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Repo Summarizer API"}


# ✅ NEW HEALTH ENDPOINT
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "repo-summarizer-api",
    }

@app.get("/health/live")
async def live():
    return {"status": "alive"}

@app.get("/health/ready")
async def ready():
    return {"status": "ready"}

@app.post("/summarize", response_model=SummarizeResponse, responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 429: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def summarize(req: SummarizeRequest):
    try:
        ref = parse_github_repo_url(str(req.github_url))
    except GitHubBadUrl as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        await assert_repo_accessible(ref)
        zip_bytes = await download_repo_zip(ref)
        tmp, repo_root = extract_zip_to_tempdir(zip_bytes)

        try:
            result = await summarize_repo(repo_root)
        finally:
            tmp.cleanup()

        return result

    except GitHubNotFound as e:
        return JSONResponse(status_code=404, content={"status": "error", "message": str(e)})
    except GitHubPrivateOrForbidden as e:
        return JSONResponse(status_code=403, content={"status": "error", "message": str(e)})
    except GitHubRateLimited as e:
        return JSONResponse(status_code=429, content={"status": "error", "message": str(e)})
    except (GitHubError, SummarizationError) as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    except Exception as e:
        # last resort — log full stack trace
        logger.exception("Unhandled error in /summarize")

        env = os.getenv("ENV", "prod").lower().strip()
        if env == "dev":
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Unexpected server error.",
                    "detail": str(e),
                },
            )

        # In non-dev environments, avoid leaking internals
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Unexpected server error.",
            },
        )