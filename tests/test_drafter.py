"""Tests for drafter and claims checking."""

import json

from linkedin_agent.context.models import CommitInfo, ProjectContext
from linkedin_agent.drafter.claims_check import audit_variant_claims
from linkedin_agent.drafter.drafter import generate_drafts
from linkedin_agent.drafter.models import ClaimItem, DraftVariant
from linkedin_agent.drafter.profile import ProfileConfig
from linkedin_agent.llm.base import LLMClient


class MockLLMClient(LLMClient):
    """Mock LLM client returning configurable string."""

    def __init__(self, response_text: str) -> None:
        self.response_text = response_text

    def complete(self, system: str, user: str) -> str:
        return self.response_text


def _sample_context() -> ProjectContext:
    return ProjectContext(
        repo="user/offline-sync-app",
        description="Offline-first Flutter app with SQLite storage",
        languages=["Dart", "Flutter"],
        topics=["offline-first", "sqlite"],
        stars=42,
        last_push="2026-10-25",
        recent_commits=[
            CommitInfo(sha="abc1234", msg="add conflict resolution algorithm", date="2026-10-24")
        ],
        readme_excerpt="Built Momentum, an offline-first app where data syncs seamlessly.",
    )


def test_claims_check_flags_unsupported() -> None:
    ctx = _sample_context()
    variant = DraftVariant(
        angle="problem-solution",
        text="Momentum is an offline app that reached 500k active users and 99.9% uptime.",
        hashtags=["#flutter"],
        claims=[
            ClaimItem(claim="Uses SQLite storage", source="README"),
            ClaimItem(claim="Replaced AWS DynamoDB with Redis", source="invention"),
        ],
    )
    warnings = audit_variant_claims(variant, ctx)
    # Should flag 500k active users and ungrounded claim about Redis
    assert any("500k" in w for w in warnings)
    assert any("Redis" in w for w in warnings)


def test_generate_drafts_success() -> None:
    ctx = _sample_context()
    mock_payload = {
        "variants": [
            {
                "angle": "problem-solution",
                "text": (
                    "Most apps fail when you lose connection.\n\n"
                    "I built Momentum, an offline Flutter app with SQLite storage.\n\n"
                    "Hardest part was conflict resolution across devices.\n\n"
                    "Repo: https://github.com/user/offline-sync-app\n\n"
                    + ("Details " * 150)
                ),
                "hashtags": ["#flutter", "#offlinefirst", "#buildinpublic"],
                "claims": [
                    {"claim": "Uses SQLite storage", "source": "README"},
                    {"claim": "Added conflict resolution algorithm", "source": "commit abc1234"},
                ],
                "warnings": [],
            }
        ],
        "missing_context": [],
    }

    client = MockLLMClient(json.dumps(mock_payload))
    profile = ProfileConfig(name="Naman", role="Engineer")
    resp = generate_drafts(ctx, llm_client=client, profile=profile)

    assert len(resp.variants) == 1
    v = resp.variants[0]
    assert v.angle == "problem-solution"
    assert len(v.claims) == 2
    assert v.claims[0].claim == "Uses SQLite storage"


def test_generate_drafts_banned_phrases() -> None:
    ctx = _sample_context()
    mock_payload = {
        "variants": [
            {
                "angle": "problem-solution",
                "text": "I am excited to announce a revolutionary game-changer app! " + ("A" * 900),
                "hashtags": ["#buildinpublic"],
                "claims": [],
                "warnings": [],
            }
        ]
    }
    client = MockLLMClient(json.dumps(mock_payload))
    profile = ProfileConfig(banned_phrases=["excited to announce", "game-changer"])
    resp = generate_drafts(ctx, llm_client=client, profile=profile)

    assert len(resp.variants) == 1
    warnings = resp.variants[0].warnings
    assert any("excited to announce" in w for w in warnings)
    assert any("game-changer" in w for w in warnings)
