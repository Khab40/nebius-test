import os

# Load .env only for local development.
# Set ENV=prod (or anything other than "dev") to disable.
if os.getenv("ENV", "dev").lower() == "dev":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        # dotenv is optional in production; if missing, rely on real env vars.
        pass
    
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
    except Exception:
        # last resort, don’t leak internals
        return JSONResponse(status_code=500, content={"status": "error", "message": "Unexpected server error."})