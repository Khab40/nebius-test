from pathlib import Path
from app.selection import select_files


def test_select_files_prefers_docs_and_configs(tmp_path: Path):
    (tmp_path / "README.md").write_text("# hi", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "big.js").write_text("x" * 1000, encoding="utf-8")

    selected = select_files(tmp_path, max_files=10)
    rels = [str(s.path.relative_to(tmp_path)) for s in selected]

    assert "README.md" in rels
    assert "pyproject.toml" in rels
    assert all(not r.startswith("node_modules") for r in rels)