"""Prompt assembly and draft generation engine."""

from __future__ import annotations

import json
import re
from typing import Any

from linkedin_agent.context.models import ProjectContext
from linkedin_agent.drafter.claims_check import audit_variant_claims
from linkedin_agent.drafter.models import ClaimItem, DraftsResponse, DraftVariant
from linkedin_agent.drafter.profile import ProfileConfig, load_profile
from linkedin_agent.llm.base import LLMClient, get_llm_client


def build_system_prompt(profile: ProfileConfig) -> str:
    """Assemble system prompt following SKILL.md guidelines and profile rules."""
    banned_list = ", ".join(f'"{p}"' for p in profile.banned_phrases)
    default_tags = ", ".join(profile.hashtags.get("default", ["#buildinpublic"]))
    min_c = profile.length.min_chars
    max_c = profile.length.max_chars
    hard_c = profile.length.hard_cap

    return f"""You are an expert LinkedIn post writer for {profile.name} ({profile.role}).
Tone: {profile.tone}.
Target Audience: {profile.audience}.

STRICT CONTENT RULES:
1. First-person voice, plain and direct language, builder-to-builder.
2. Short paragraphs (1–2 sentences), generous blank line spacing.
3. Length: between {min_c} and {max_c} characters (hard cap {hard_c}).
4. Maximum {profile.max_emojis} emojis in the entire post.
5. Lead with problem/outcome. NEVER use "Excited to announce", "Thrilled", "Humbled".
6. Absolutely NO banned phrases: {banned_list}.
7. ZERO FABRICATION: Do not invent numbers, benchmarks, user counts, or unverified claims.
8. Include soft CTA at the end (e.g. repo link or question).
9. Include 3–5 relevant hashtags (such as {default_tags}).
10. Generate 2 to 3 distinct variants, each taking a unique angle:
    - Variant 1: Problem -> Solution
    - Variant 2: Deep-dive into a technical challenge or architecture decision
    - Variant 3: Key lesson learned or milestone reflection

OUTPUT FORMAT:
Respond with ONLY valid JSON adhering to this exact schema:
{{
  "variants": [
    {{
      "angle": "problem-solution",
      "text": "Post text with \\n line breaks",
      "hashtags": ["#buildinpublic", "#python"],
      "claims": [
        {{"claim": "Uses SQLite for state", "source": "README"}},
        {{"claim": "Added offline sync", "source": "commit 1a2b3c4"}}
      ],
      "warnings": []
    }}
  ],
  "missing_context": []
}}
"""


def build_user_prompt(ctx: ProjectContext, instruction: str | None = None) -> str:
    """Format ProjectContext into structured user prompt."""
    commits_text = "\n".join(f"- [{c.sha}] {c.msg} ({c.date})" for c in ctx.recent_commits)
    releases_text = "\n".join(f"- [{r.tag}] {r.name}: {r.body or ''}" for r in ctx.releases)

    prompt = f"""Generate LinkedIn post variants for the following project:

Repository: {ctx.repo}
Description: {ctx.description or 'None'}
Languages: {', '.join(ctx.languages)}
Topics: {', '.join(ctx.topics)}
Stars: {ctx.stars}
Homepage: {ctx.homepage or 'None'}

README Excerpt:
{ctx.readme_excerpt or 'None provided'}

Recent Commits:
{commits_text or 'None'}

Releases:
{releases_text or 'None'}

Local Notes:
{ctx.local_notes or 'None'}
"""
    if instruction:
        prompt += f"\nAdditional User Instruction:\n{instruction}\n"

    return prompt


def _clean_json_text(text: str) -> str:
    """Extract JSON object from markdown code fences if present."""
    trimmed = text.strip()
    if trimmed.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", trimmed)
        if match:
            return match.group(1).strip()
    return trimmed


def generate_drafts(
    ctx: ProjectContext,
    llm_client: LLMClient | None = None,
    profile: ProfileConfig | None = None,
    instruction: str | None = None,
) -> DraftsResponse:
    """Generate and validate post variants for repository context."""
    client = llm_client or get_llm_client()
    cfg = profile or load_profile()

    system_prompt = build_system_prompt(cfg)
    user_prompt = build_user_prompt(ctx, instruction)

    raw_response = client.complete(system=system_prompt, user=user_prompt)
    clean_json = _clean_json_text(raw_response)

    try:
        parsed: dict[str, Any] = json.loads(clean_json)
    except json.JSONDecodeError as exc:
        # Fallback empty response with parsing warning
        snippet = raw_response[:100]
        return DraftsResponse(
            variants=[],
            missing_context=[f"LLM produced invalid JSON: {exc}. Snippet: {snippet}"],
        )

    raw_variants = parsed.get("variants", [])
    variants: list[DraftVariant] = []

    for item in raw_variants:
        text = str(item.get("text", "")).strip()
        angle = str(item.get("angle", "general"))
        hashtags = [str(h) for h in item.get("hashtags", [])]
        raw_claims = item.get("claims", [])
        claims = [
            ClaimItem(claim=str(c.get("claim", "")), source=str(c.get("source", "")))
            for c in raw_claims
            if isinstance(c, dict)
        ]
        warnings = [str(w) for w in item.get("warnings", [])]

        # 1. Banned phrases check
        for banned in cfg.banned_phrases:
            if re.search(r"\b" + re.escape(banned) + r"\b", text, re.IGNORECASE):
                warnings.append(f"Contains banned phrase: '{banned}'")

        # 2. Length check
        if len(text) < cfg.length.min_chars:
            warnings.append(f"Text too short ({len(text)} chars < min {cfg.length.min_chars})")
        elif len(text) > cfg.length.hard_cap:
            warnings.append(
                f"Text exceeds hard cap ({len(text)} chars > max {cfg.length.hard_cap})"
            )

        # 3. Emojis check
        emoji_count = len(re.findall(r"[\U00010000-\U0010ffff]", text))
        if emoji_count > cfg.max_emojis:
            warnings.append(f"Too many emojis ({emoji_count} > max {cfg.max_emojis})")

        variant = DraftVariant(
            angle=angle,
            text=text,
            hashtags=hashtags,
            claims=claims,
            warnings=warnings,
        )

        # 4. Claims grounding audit
        variant.warnings = audit_variant_claims(variant, ctx)
        variants.append(variant)

    missing_ctx = [str(m) for m in parsed.get("missing_context", [])]
    return DraftsResponse(variants=variants, missing_context=missing_ctx)
