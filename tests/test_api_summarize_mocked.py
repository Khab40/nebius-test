import respx
from fastapi.testclient import TestClient

from app.main import app


def test_summarize_happy_path_mocked(monkeypatch, sample_repo_zip_bytes):
    # Ensure provider config doesn't fail even if some code checks env vars.
    monkeypatch.setenv("ENV", "dev")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test")

    # Mock LLM call (no external network)
    async def fake_chat_completion(*args, **kwargs):
        return '{"summary":"demo","technologies":["Python"],"structure":"app/ + docs"}'

    monkeypatch.setattr("app.summarize.chat_completion", fake_chat_completion)

    # Mock GitHub calls. Different implementations use different URLs:
    # - codeload.github.com/{org}/{repo}/zip/refs/heads/{branch}
    # - github.com/{org}/{repo}/archive/refs/heads/{branch}.zip
    # - api.github.com/repos/{org}/{repo} (to find default_branch)
    with respx.mock(assert_all_called=False) as rs:
        rs.get(url__regex=r"https://codeload\\.github\\.com/.+?/zip/refs/heads/.+").respond(
            200, content=sample_repo_zip_bytes, headers={"Content-Type": "application/zip"}
        )
        rs.get(url__regex=r"https://github\\.com/.+?/archive/refs/heads/.+\\.zip").respond(
            200, content=sample_repo_zip_bytes, headers={"Content-Type": "application/zip"}
        )
        rs.get(url__regex=r"https://api\\.github\\.com/repos/.+?/.+").respond(
            200,
            json={"default_branch": "main"},
            headers={"Content-Type": "application/json"},
        )

        # Some implementations use GitHub API zipball endpoints
        rs.get(url__regex=r"https://api\\.github\\.com/repos/.+?/.+/(zipball|tarball).*").respond(
            200, content=sample_repo_zip_bytes, headers={"Content-Type": "application/zip"}
        )

        # Some implementations may fetch README via raw.githubusercontent.com
        rs.get(url__regex=r"https://raw\\.githubusercontent\\.com/.+?/README\\.md").respond(
            200, text="# Demo Repo\n", headers={"Content-Type": "text/plain"}
        )

        # Very broad safety net for any GitHub-hosted zip URL variants
        rs.get(url__regex=r"https://(codeload\\.github\\.com|github\\.com)/.+?\\.zip").respond(
            200, content=sample_repo_zip_bytes, headers={"Content-Type": "application/zip"}
        )

        client = TestClient(app)
        resp = client.post("/summarize", json={"github_url": "https://github.com/org/repo"})

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["summary"] == "demo"
        assert "Python" in data["technologies"]