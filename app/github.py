import io, re, zipfile, tempfile, httpx
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

GITHUB_REPO_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?]+)(?:/|$)"
)


class GitHubError(Exception):
    pass


class GitHubNotFound(GitHubError):
    pass


class GitHubPrivateOrForbidden(GitHubError):
    pass


class GitHubRateLimited(GitHubError):
    pass


class GitHubBadUrl(GitHubError):
    pass


@dataclass(frozen=True)
class RepoRef:
    owner: str
    repo: str


def parse_github_repo_url(url: str) -> RepoRef:
    m = GITHUB_REPO_RE.match(url.strip())
    if not m:
        raise GitHubBadUrl("github_url must look like https://github.com/<owner>/<repo>")
    owner = m.group("owner")
    repo = m.group("repo")
    # strip .git if provided
    if repo.endswith(".git"):
        repo = repo[:-4]
    return RepoRef(owner=owner, repo=repo)


async def _github_api_get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    # No auth required for public repos; rate-limited by GitHub.
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "repo-summarizer-api",
    }
    return await client.get(url, headers=headers, follow_redirects=True, timeout=30.0)


async def assert_repo_accessible(ref: RepoRef) -> dict:
    api_url = f"https://api.github.com/repos/{ref.owner}/{ref.repo}"
    async with httpx.AsyncClient() as client:
        r = await _github_api_get(client, api_url)

    if r.status_code == 404:
        raise GitHubNotFound("Repository not found (404).")
    if r.status_code in (401, 403):
        # Could be private or rate-limit. Check headers.
        remaining = r.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            raise GitHubRateLimited("GitHub API rate limit exceeded. Try again later.")
        raise GitHubPrivateOrForbidden("Repository is private or access is forbidden (403).")
    if r.status_code >= 400:
        raise GitHubError(f"GitHub API error ({r.status_code}).")

    data = r.json()
    # If GitHub marks it private, treat as forbidden for this task.
    if data.get("private") is True:
        raise GitHubPrivateOrForbidden("Repository is private.")
    return data


async def download_repo_zip(ref: RepoRef) -> bytes:
    # zipball works for default branch
    url = f"https://api.github.com/repos/{ref.owner}/{ref.repo}/zipball"
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "repo-summarizer-api"},
            follow_redirects=True,
            timeout=60.0,
        )

    if r.status_code == 404:
        raise GitHubNotFound("Repository not found (404).")
    if r.status_code in (401, 403):
        remaining = r.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            raise GitHubRateLimited("GitHub API rate limit exceeded. Try again later.")
        raise GitHubPrivateOrForbidden("Repository is private or access is forbidden (403).")
    if r.status_code >= 400:
        raise GitHubError(f"GitHub ZIP download failed ({r.status_code}).")

    return r.content


def extract_zip_to_tempdir(zip_bytes: bytes) -> Tuple[tempfile.TemporaryDirectory, Path]:
    tmp = tempfile.TemporaryDirectory(prefix="repozip_")
    root = Path(tmp.name)

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(root)
    except zipfile.BadZipFile as e:
        tmp.cleanup()
        raise GitHubError("Downloaded archive is not a valid ZIP.") from e

    # GitHub zipball contains a single top-level directory
    children = [p for p in root.iterdir() if p.is_dir()]
    repo_root = children[0] if children else root
    return tmp, repo_root