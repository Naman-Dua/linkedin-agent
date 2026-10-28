# RULES — LinkedIn Post Agent

Applies to: the agent at runtime, and any AI/human contributor editing the code.

## A. Hard Rules (never violate)
1. **No post without explicit approval.** The publisher must verify an `Approval` record whose `text_sha256` equals the hash of the exact text being sent.
2. **Any edit invalidates approval.** Changed text → new hash → re-approve.
3. **`DRY_RUN` defaults to true.** Only the user flips it.
4. **Never invent facts.** No fabricated metrics, users, awards, employers, quotes, or results. Every claim must trace to context (repo data, local notes, commits).
5. **Never expose secrets.** No tokens/keys/emails/internal URLs in prompts, drafts, logs, or commits.
6. **Private repos are opt-in** per repo in `config.yaml`.
7. **Only act on the user's own account.** No engagement automation (likes, comments, DMs, connection requests).
8. **Audit everything.** Every draft, decision, and publish call is logged.

## B. Content Rules (drafts)
- Voice: first person, plain, specific, builder-to-builder. Match `profile.yaml`.
- Length: 900–1,500 chars default; hard cap 3,000.
- Structure: hook (line 1–2) → problem → what I built → stack → challenge/learning → CTA → 3–5 hashtags.
- Short paragraphs, 1–2 sentences each; line breaks for readability.
- Lead with the problem or outcome, not "I'm excited to announce".
- Include the repo/demo link when available.
- Banned: buzzword stacks, "game-changer", "revolutionary", "thrilled", "humbled", emoji spam (max 2), engagement bait ("Agree?"), fake humility, unverified superlatives.
- Don't claim "production-ready", "scalable", etc. unless the context states it.
- Don't mention other people/companies unless in the context and relevant (e.g., Digital Markitors only if the user's notes say to).
- Each variant must differ in hook and angle, not just wording.

## C. Code Rules
- Python 3.11+, type hints everywhere, `mypy --strict` clean, `ruff` clean.
- Small modules; one responsibility each; interfaces in `base.py` files.
- Pure functions for logic; side effects (network/DB/FS) at edges.
- No global state; config via a single typed `Settings` object.
- Network calls: timeouts, retries with backoff, typed errors.
- Tests for every module; mock network; no real API calls in CI.
- Never commit `.env`, tokens, DB files, or real API responses with private data.
- Commit style: Conventional Commits (`feat:`, `fix:`, `docs:`).
- Don't add dependencies without a stated reason.

## D. Agent Behavior Rules
- Ask the user only when blocked; otherwise state assumptions and proceed.
- If context is thin (no README, no commits), say so and ask for notes instead of padding.
- On claims-check failure: regenerate once, then surface warnings in the approval UI.
- On LinkedIn error: do not retry blindly; check whether the post already exists first.
- Prefer failing closed (no post) over failing open.

## E. Definition of Done (any change)
- [ ] Tests pass, lint/type clean
- [ ] No new path to publish that bypasses the gate
- [ ] Docs updated if behavior changed
