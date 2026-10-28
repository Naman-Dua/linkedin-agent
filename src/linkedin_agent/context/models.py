"""Domain data models for project context."""

from pydantic import BaseModel, Field


class CommitInfo(BaseModel):
    """Summarized Git commit."""

    sha: str
    msg: str
    date: str


class ReleaseInfo(BaseModel):
    """Summarized release information."""

    tag: str
    name: str
    date: str
    body: str | None = None


class ProjectContext(BaseModel):
    """Aggregated, sanitized context for a repository."""

    repo: str
    description: str | None = None
    readme_excerpt: str | None = None
    languages: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    recent_commits: list[CommitInfo] = Field(default_factory=list)
    releases: list[ReleaseInfo] = Field(default_factory=list)
    homepage: str | None = None
    stars: int = 0
    local_notes: str | None = None
    last_push: str | None = None
