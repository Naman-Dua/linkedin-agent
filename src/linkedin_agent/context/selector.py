"""Repository selection and ranking engine."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel

from linkedin_agent.ingest.github import GitHubClient
from linkedin_agent.store.db import Database


class RepoScore(BaseModel):
    """Scored repository recommendation."""

    repo: str
    total_score: float
    activity_score: float
    unposted_score: float
    readme_score: float
    is_posted: bool
    last_pushed_days_ago: int
    reason: str


class SelectorConfig(BaseModel):
    """Configuration for repository filtering and scoring weights."""

    allowlist: list[str] = []
    denylist: list[str] = []
    allow_private: list[str] = []
    activity_weight: float = 0.4
    unposted_weight: float = 0.4
    readme_weight: float = 0.2


def load_selector_config(config_path: Path | None = None) -> SelectorConfig:
    """Load configuration from config.yaml or return defaults."""
    target = config_path or (Path.cwd() / "config.yaml")
    if target.exists():
        try:
            data = yaml.safe_load(target.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                repos_cfg = data.get("repos", {})
                weights_cfg = data.get("selection_weights", {})
                return SelectorConfig(
                    allowlist=repos_cfg.get("allowlist", []),
                    denylist=repos_cfg.get("denylist", []),
                    allow_private=repos_cfg.get("allow_private", []),
                    activity_weight=float(weights_cfg.get("activity", 0.4)),
                    unposted_weight=float(weights_cfg.get("unposted", 0.4)),
                    readme_weight=float(weights_cfg.get("readme_quality", 0.2)),
                )
        except Exception:
            pass
    return SelectorConfig()


def calculate_activity_score(pushed_at_str: str | None) -> tuple[float, int]:
    """Calculate recency score (0.0 to 1.0) and days since last push."""
    if not pushed_at_str:
        return 0.1, 999

    try:
        # Standardize ISO timestamp
        clean_date = pushed_at_str.replace("Z", "+00:00")
        pushed_at = datetime.fromisoformat(clean_date)
        days = max(0, (datetime.now(UTC) - pushed_at).days)

        if days <= 7:
            return 1.0, days
        elif days <= 30:
            return 0.75, days
        elif days <= 90:
            return 0.4, days
        else:
            return 0.1, days
    except Exception:
        return 0.1, 999


def rank_repositories(
    gh: GitHubClient,
    db: Database,
    config: SelectorConfig | None = None,
    user: str | None = None,
) -> list[RepoScore]:
    """Rank candidate repositories by activity, unposted status, and content quality."""
    cfg = config or load_selector_config()
    raw_repos = gh.list_repos(user=user)
    scores: list[RepoScore] = []

    for r in raw_repos:
        name = str(r.get("name", ""))
        full_name = str(r.get("full_name", name))
        is_private = bool(r.get("private", False))

        # 1. Apply Filters
        if full_name in cfg.denylist or name in cfg.denylist:
            continue
        if cfg.allowlist and full_name not in cfg.allowlist and name not in cfg.allowlist:
            continue
        if is_private and full_name not in cfg.allow_private and name not in cfg.allow_private:
            continue

        # 2. Activity Score
        pushed_at = r.get("pushed_at")
        act_score, days_ago = calculate_activity_score(str(pushed_at) if pushed_at else None)

        # 3. Unposted Score
        is_posted = db.has_repo_been_posted(full_name) or db.has_repo_been_posted(name)
        unposted_score = 0.0 if is_posted else 1.0

        # 4. Content / README Quality Score
        has_desc = bool(r.get("description"))
        has_topics = bool(r.get("topics"))
        readme_score = 1.0 if (has_desc and has_topics) else (0.6 if has_desc else 0.2)

        # 5. Composite Score
        total = (
            cfg.activity_weight * act_score
            + cfg.unposted_weight * unposted_score
            + cfg.readme_weight * readme_score
        )

        reason_parts: list[str] = []
        if is_posted:
            reason_parts.append("Already posted")
        else:
            reason_parts.append("Not yet posted")
        reason_parts.append(f"pushed {days_ago}d ago")
        if has_desc:
            reason_parts.append("has description")

        scores.append(
            RepoScore(
                repo=full_name,
                total_score=round(total, 3),
                activity_score=act_score,
                unposted_score=unposted_score,
                readme_score=readme_score,
                is_posted=is_posted,
                last_pushed_days_ago=days_ago,
                reason=", ".join(reason_parts),
            )
        )

    # Sort descending by total score
    scores.sort(key=lambda s: s.total_score, reverse=True)
    return scores
