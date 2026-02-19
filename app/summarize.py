import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from .selection import build_tree, select_files, safe_read_text, detect_languages_and_tools
from .nebius import chat_completion, NebiusError


class SummarizationError(Exception):
    pass


JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def build_context(repo_root: Path, max_total_chars: int = 22000) -> str:
    """
    Strategy (matches your prompt):
    1) README + important docs
    2) Directory tree
    3) Config files for deps/tech
    4) “endpoint-ish” files and main modules with comments/docstrings
    5) Hard cap to fit LLM context
    """
    parts: List[str] = []

    tree = build_tree(repo_root, max_depth=4)
    parts.append("=== DIRECTORY TREE (truncated) ===\n" + tree)

    selected = select_files(repo_root, max_files=28)

    # Per-file caps: docs bigger, code smaller
    def per_file_cap(p: Path) -> int:
        name = p.name.lower()
        if "readme" in name:
            return 6000
        if name in {"pyproject.toml", "requirements.txt", "package.json"}:
            return 3000
        if name.startswith(("openapi", "swagger")):
            return 4000
        return 2000

    # Add files until max_total_chars reached
    total = sum(len(x) for x in parts)
    for sf in selected:
        rel = sf.path.relative_to(repo_root)
        text = safe_read_text(sf.path, max_chars=per_file_cap(sf.path))
        if not text.strip():
            continue
        chunk = f"\n\n=== FILE: {rel} ===\n{text}"
        if total + len(chunk) > max_total_chars:
            break
        parts.append(chunk)
        total += len(chunk)

    return "\n".join(parts)


def parse_llm_json(text: str) -> Dict:
    # Try direct JSON first
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try extracting a JSON object from within text
    m = JSON_BLOCK_RE.search(text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    raise SummarizationError("LLM response was not valid JSON.")


async def summarize_repo(repo_root: Path) -> Dict:
    langs = detect_languages_and_tools(repo_root)
    context = build_context(repo_root)

    system = (
        "You are a senior software engineer. "
        "Given a GitHub repository snapshot, produce a concise, human-readable summary."
    )

    user = f"""
Return ONLY valid JSON with keys: summary (string), technologies (array of strings), structure (string).

Rules:
- summary: what the project does (2-6 sentences).
- technologies: include programming languages + key frameworks/libraries you can infer from config files and code (dedupe).
- structure: describe the layout (where main code lives, tests, docs, configs) in 2-5 sentences.
- If unsure, be explicit (e.g., 'appears to', 'likely').

Repository signals:
Detected languages/tools (heuristic): {langs}

Repository content (filtered & truncated):
{context}
""".strip()

    try:
        out = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
    except NebiusError as e:
        raise SummarizationError(str(e)) from e

    data = parse_llm_json(out)

    # Normalize fields
    summary = str(data.get("summary", "")).strip()
    technologies = data.get("technologies", [])
    structure = str(data.get("structure", "")).strip()

    if not summary or not structure or not isinstance(technologies, list):
        raise SummarizationError("LLM JSON missing required fields.")

    technologies = [str(x).strip() for x in technologies if str(x).strip()]
    # add heuristic langs if LLM missed them
    for l in langs:
        if l not in technologies:
            technologies.append(l)

    return {"summary": summary, "technologies": technologies, "structure": structure}