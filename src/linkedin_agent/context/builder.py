"""Context builder module to merge, redact, and budget repository context."""

from __future__ import annotations

from typing import Any

from linkedin_agent.context.models import CommitInfo, ProjectContext, ReleaseInfo
from linkedin_agent.context.redaction import redact_text
from linkedin_agent.ingest.github import GitHubClient
from linkedin_agent.ingest.local import load_local_notes

# Token & character budget limits
MAX_README_CHARS = 2000
MAX_COMMIT_MSG_CHARS = 120
MAX_RELEASE_BODY_CHARS = 300


def trim_text(text: str | None, max_chars: int) -> str | None:
    """Trim text to maximum character budget without cutting words in half."""
    if not text or len(text) <= max_chars:
        return text
    trimmed = text[:max_chars].rsplit(" ", 1)[0]
    return f"{trimmed}..."


def build_project_context(
    repo_spec: str,
    github_client: GitHubClient | None = None,
    client: GitHubClient | None = None,
) -> ProjectContext:
    """Assemble sanitized, budgeted ProjectContext from GitHub API and local notes."""
    gh = github_client or client or GitHubClient()
    owner, repo_name = gh.parse_repo_path(repo_spec)

    # 1. Fetch raw GitHub information
    raw_repo = gh.get_repo(owner, repo_name)
    raw_readme = gh.get_readme(owner, repo_name)
    raw_languages = gh.get_languages(owner, repo_name)
    raw_commits = gh.get_commits(owner, repo_name, limit=5)
    raw_releases = gh.get_releases(owner, repo_name, limit=3)

    # 2. Fetch local notes
    raw_notes = load_local_notes(repo_name)

    # 3. Sanitize and trim README
    readme_sanitized = redact_text(raw_readme)
    readme_excerpt = trim_text(readme_sanitized, MAX_README_CHARS)

    # 4. Parse commits
    commits: list[CommitInfo] = []
    for c in raw_commits:
        commit_data: dict[str, Any] = c.get("commit", {})
        sha = str(c.get("sha", ""))[:7]
        msg_raw = str(commit_data.get("message", ""))
        msg = msg_raw.splitlines()[0] if msg_raw else ""
        msg_sanitized = redact_text(msg) or ""
        msg_trimmed = trim_text(msg_sanitized, MAX_COMMIT_MSG_CHARS) or ""
        author_data: dict[str, Any] = commit_data.get("author", {})
        date = str(author_data.get("date", ""))
        if sha:
            commits.append(CommitInfo(sha=sha, msg=msg_trimmed, date=date))

    # 5. Parse releases
    releases: list[ReleaseInfo] = []
    for r in raw_releases:
        tag = str(r.get("tag_name", ""))
        name = str(r.get("name", "") or tag)
        date = str(r.get("published_at", "") or r.get("created_at", ""))
        body = redact_text(r.get("body"))
        body_trimmed = trim_text(body, MAX_RELEASE_BODY_CHARS)
        if tag:
            releases.append(ReleaseInfo(tag=tag, name=name, date=date, body=body_trimmed))

    # 6. Sanitize local notes
    notes_sanitized = redact_text(raw_notes)

    # 7. Extract metadata
    desc = redact_text(raw_repo.get("description"))
    homepage = raw_repo.get("homepage") or None
    stars = int(raw_repo.get("stargazers_count", 0))
    last_push = str(raw_repo.get("pushed_at", ""))
    topics = list(raw_repo.get("topics", []))

    return ProjectContext(
        repo=f"{owner}/{repo_name}",
        description=desc,
        readme_excerpt=readme_excerpt,
        languages=raw_languages,
        topics=topics,
        recent_commits=commits,
        releases=releases,
        homepage=homepage,
        stars=stars,
        local_notes=notes_sanitized,
        last_push=last_push,
    )
