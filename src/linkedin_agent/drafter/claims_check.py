"""Grounding and claims verification module."""

from __future__ import annotations

import re

from linkedin_agent.context.models import ProjectContext
from linkedin_agent.drafter.models import DraftVariant


def _extract_context_corpus(ctx: ProjectContext) -> str:
    """Build a normalized text corpus from all verified context fields."""
    parts: list[str] = [
        ctx.repo,
        ctx.description or "",
        ctx.readme_excerpt or "",
        " ".join(ctx.languages),
        " ".join(ctx.topics),
        ctx.local_notes or "",
    ]
    for c in ctx.recent_commits:
        parts.append(f"{c.sha} {c.msg}")
    for r in ctx.releases:
        parts.append(f"{r.tag} {r.name} {r.body or ''}")
    return " ".join(parts).lower()


COMMON_STOP_WORDS = {
    "with", "from", "that", "this", "have", "been", "were", "what",
    "when", "where", "which", "will", "would", "could", "should",
    "into", "about", "more", "most", "some", "such", "only", "also",
    "then", "than", "other", "using", "uses", "used", "after", "before",
}


def audit_variant_claims(variant: DraftVariant, ctx: ProjectContext) -> list[str]:
    """Audit claims in a draft variant against context corpus.

    Returns a list of warnings for any ungrounded assertions or metric fabrications.
    """
    corpus = _extract_context_corpus(ctx)
    warnings: list[str] = list(variant.warnings)

    # 1. Check for fabricated metrics/numbers in text not present in context
    # Find numbers with units like 10k, 100%, 500ms, 1000 users, etc.
    metric_pattern = re.compile(
        r"\b\d+(?:\.\d+)?(?:k|m|%|x|ms|s)?\b",
        re.IGNORECASE,
    )
    text_numbers = {m.group(0).lower() for m in metric_pattern.finditer(variant.text)}
    corpus_numbers = {m.group(0).lower() for m in metric_pattern.finditer(corpus)}

    for num in text_numbers:
        # Ignore common non-metric small numbers like 1, 2, 3 in bullet points
        if num in {"1", "2", "3", "4", "5", "10", "20"}:
            continue
        if num not in corpus_numbers:
            warnings.append(f"Potentially unverified metric or number: '{num}'")

    # 2. Check each declared claim item
    for item in variant.claims:
        claim_words = [
            w
            for w in re.findall(r"\w+", item.claim.lower())
            if len(w) > 3 and w not in COMMON_STOP_WORDS
        ]
        if not claim_words:
            continue
        # If fewer than 50% of the significant claim words appear in corpus, flag it
        matches = [w for w in claim_words if w in corpus]
        if len(matches) / len(claim_words) < 0.5:
            warnings.append(
                f"Claim appears unsupported by context: '{item.claim}' (source: {item.source})"
            )

    return list(dict.fromkeys(warnings))
