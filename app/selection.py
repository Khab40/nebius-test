import os, re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

# Ignore bulky / irrelevant folders and files
IGNORE_DIRS = {
    ".git", ".github", ".idea", ".vscode",
    "node_modules", "dist", "build", "target", ".next", ".cache",
    "venv", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".tox", ".ruff_cache", ".gradle", ".terraform",
}

IGNORE_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".7z",
    ".mp4", ".mov", ".avi", ".mp3",
    ".exe", ".dll", ".so", ".dylib",
    ".class", ".jar",
    ".bin",
}

IGNORE_FILES_EXACT = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "poetry.lock", "Pipfile.lock",
}

IMPORTANT_DOC_NAMES = [
    "README.md", "README.rst", "README.txt",
    "CONTRIBUTING.md", "CHANGELOG.md", "LICENSE", "LICENSE.md",
    "SECURITY.md", "CODE_OF_CONDUCT.md",
]

IMPORTANT_CONFIG_NAMES = [
    "pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "Pipfile",
    "package.json", "tsconfig.json",
    "go.mod", "Cargo.toml", "Gemfile",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", ".editorconfig",
    "Makefile",
    "openapi.yaml", "openapi.yml", "openapi.json",
    "swagger.yaml", "swagger.yml", "swagger.json",
]

CODE_EXTS = {".py", ".js", ".ts", ".tsx", ".java", ".go", ".rs", ".cs", ".rb", ".php"}


@dataclass
class SelectedFile:
    path: Path
    score: int


def is_ignored_path(p: Path) -> bool:
    # directory ignore
    for part in p.parts:
        if part in IGNORE_DIRS:
            return True
    # file ignore
    if p.name in IGNORE_FILES_EXACT:
        return True
    if p.suffix.lower() in IGNORE_EXTS:
        return True
    return False


def build_tree(repo_root: Path, max_depth: int = 4, max_entries: int = 400) -> str:
    lines: List[str] = []
    count = 0

    def walk(dir_path: Path, depth: int):
        nonlocal count
        if depth > max_depth or count >= max_entries:
            return
        try:
            entries = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except Exception:
            return
        for e in entries:
            if count >= max_entries:
                return
            rel = e.relative_to(repo_root)
            if is_ignored_path(rel):
                continue
            indent = "  " * depth
            lines.append(f"{indent}- {e.name}{'/' if e.is_dir() else ''}")
            count += 1
            if e.is_dir():
                walk(e, depth + 1)

    walk(repo_root, 0)
    if count >= max_entries:
        lines.append("... (tree truncated)")
    return "\n".join(lines)


def score_file(repo_root: Path, f: Path) -> int:
    rel = f.relative_to(repo_root)
    name = f.name
    score = 0

    # docs/configs highest priority
    if name in IMPORTANT_DOC_NAMES:
        score += 1000
    if name in IMPORTANT_CONFIG_NAMES:
        score += 900

    # common project docs
    if rel.parts and rel.parts[0].lower() in {"docs", "doc"}:
        score += 300
    if "readme" in name.lower():
        score += 600

    # API specs & endpoints hints
    if name.lower().startswith(("openapi", "swagger")):
        score += 800
    if any(k in name.lower() for k in ["routes", "router", "controllers", "endpoints"]):
        score += 250

    # prefer smaller, top-level, and "main" style files
    if len(rel.parts) <= 2:
        score += 120
    if name.lower() in {"main.py", "app.py", "server.py", "index.js", "index.ts"}:
        score += 200

    # code files get baseline priority
    if f.suffix.lower() in CODE_EXTS:
        score += 80

    # penalize very deep paths
    score -= 10 * max(0, len(rel.parts) - 5)

    return score


def select_files(repo_root: Path, max_files: int = 28) -> List[SelectedFile]:
    candidates: List[SelectedFile] = []
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(repo_root)
        if is_ignored_path(rel):
            continue
        try:
            # skip huge files
            if p.stat().st_size > 350_000:
                continue
        except OSError:
            continue

        candidates.append(SelectedFile(path=p, score=score_file(repo_root, p)))

    candidates.sort(key=lambda x: x.score, reverse=True)
    return candidates[:max_files]


def safe_read_text(path: Path, max_chars: int) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        try:
            data = path.read_text(encoding="latin-1", errors="replace")
        except Exception:
            return ""
    if len(data) > max_chars:
        return data[:max_chars] + "\n... (truncated)"
    return data


def detect_languages_and_tools(repo_root: Path) -> List[str]:
    # lightweight detection via extensions + common files
    langs = set()
    exts = set()

    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(repo_root)
        if is_ignored_path(rel):
            continue
        exts.add(p.suffix.lower())
        if p.name == "pyproject.toml" or p.name == "requirements.txt" or p.name == "setup.py":
            langs.add("Python")
        if p.name == "package.json":
            langs.add("Node.js")
        if p.name == "go.mod":
            langs.add("Go")
        if p.name == "Cargo.toml":
            langs.add("Rust")
        if p.name.lower().startswith("dockerfile") or p.name in {"docker-compose.yml", "docker-compose.yaml"}:
            langs.add("Docker")

    if ".ts" in exts or ".tsx" in exts:
        langs.add("TypeScript")
    if ".js" in exts:
        langs.add("JavaScript")
    if ".py" in exts:
        langs.add("Python")
    if ".java" in exts:
        langs.add("Java")
    if ".go" in exts:
        langs.add("Go")
    if ".rs" in exts:
        langs.add("Rust")

    return sorted(langs)