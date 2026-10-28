"""Profile configuration loader and validator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class LengthConstraints(BaseModel):
    min_chars: int = 900
    max_chars: int = 1500
    hard_cap: int = 3000


class ProfileConfig(BaseModel):
    name: str = "Developer"
    role: str = "Software Engineer"
    tone: str = "builder-to-builder, plain language, direct, technical"
    audience: str = "developers, engineering leads, founders"
    length: LengthConstraints = Field(default_factory=LengthConstraints)
    max_emojis: int = 2
    hashtags: dict[str, Any] = Field(
        default_factory=lambda: {
            "default": ["#buildinpublic", "#softwareengineering"],
            "max_count": 5,
        }
    )
    banned_phrases: list[str] = Field(
        default_factory=lambda: [
            "excited to announce",
            "game-changer",
            "revolutionary",
            "thrilled to share",
            "humbled and honored",
            "agree?",
        ]
    )
    cta_styles: list[str] = Field(default_factory=list)
    examples: list[dict[str, str]] = Field(default_factory=list)


def load_profile(path: Path | None = None) -> ProfileConfig:
    """Load profile configuration from YAML file or return defaults."""
    target_path = path or (Path.cwd() / "profile.yaml")
    if target_path.exists():
        try:
            data = yaml.safe_load(target_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return ProfileConfig(**data)
        except Exception:
            pass
    return ProfileConfig()
