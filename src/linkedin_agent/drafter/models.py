"""Data models for draft generation and claims checking."""

from pydantic import BaseModel, Field


class ClaimItem(BaseModel):
    """A factual claim cited in a draft post."""

    claim: str
    source: str


class DraftVariant(BaseModel):
    """A generated LinkedIn post variant."""

    angle: str
    text: str
    hashtags: list[str] = Field(default_factory=list)
    claims: list[ClaimItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DraftsResponse(BaseModel):
    """Collection of generated draft variants."""

    variants: list[DraftVariant] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)
