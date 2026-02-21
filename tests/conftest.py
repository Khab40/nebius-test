import io
import zipfile
import pytest

import sys
from pathlib import Path

# Ensure repo root is on sys.path so `import app` works in tests.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

@pytest.fixture()
def sample_repo_zip_bytes() -> bytes:
    """In-memory ZIP that looks like a tiny public repo."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "repo-main/README.md",
            "# Demo Repo\n\nThis is a demo.\n\n## Install\n\n```bash\npip install -r requirements.txt\n```\n",
        )
        z.writestr("repo-main/requirements.txt", "fastapi\nhttpx\n")
        z.writestr(
            "repo-main/app/main.py",
            "from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/health')\ndef health():\n    return {'status':'ok'}\n",
        )
        z.writestr(
            "repo-main/app/api.py",
            "from fastapi import APIRouter\nrouter = APIRouter()\n\n@router.post('/summarize')\ndef summarize():\n    return {}\n",
        )
    return buf.getvalue()