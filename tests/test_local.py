"""Tests for local project notes reader."""

from pathlib import Path

from linkedin_agent.ingest.local import load_local_notes


def test_load_local_notes_found(tmp_path: Path) -> None:
    notes_file = tmp_path / "my-repo.md"
    notes_file.write_text("# Project Notes\nBuilt offline sync.", encoding="utf-8")

    result = load_local_notes("my-repo", base_dir=tmp_path)
    assert result == "# Project Notes\nBuilt offline sync."


def test_load_local_notes_not_found(tmp_path: Path) -> None:
    result = load_local_notes("nonexistent", base_dir=tmp_path)
    assert result is None


def test_load_local_notes_path_traversal(tmp_path: Path) -> None:
    # Attempt to break out of base_dir
    result = load_local_notes("../../etc/passwd", base_dir=tmp_path)
    assert result is None
