"""Local notes reader for projects/*.md."""

from pathlib import Path


def load_local_notes(repo_name: str, base_dir: Path | None = None) -> str | None:
    """Read local project notes for a given repo name safely.

    Checks projects/<repo_name>.md and projects/<repo_name_normalized>.md.
    Protects against path traversal attacks.
    """
    if not base_dir:
        base_dir = Path.cwd() / "projects"

    base_resolved = base_dir.resolve()
    if not base_resolved.exists():
        return None

    # Sanitize candidate filenames
    candidates = [
        f"{repo_name}.md",
        f"{repo_name.lower()}.md",
        f"{repo_name.replace('/', '_')}.md",
        f"{repo_name.split('/')[-1]}.md",
    ]

    for candidate in candidates:
        note_path = (base_resolved / candidate).resolve()
        # Verify note_path is strictly within base_resolved to prevent path traversal
        try:
            note_path.relative_to(base_resolved)
        except ValueError:
            continue

        if note_path.is_file():
            return note_path.read_text(encoding="utf-8")

    return None
