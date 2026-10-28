# PRD — LinkedIn Post Agent

**Owner:** Naman | **Status:** Draft v1 | **Type:** Personal tool

## 1. Problem
Shipping projects is easy; writing and posting about them consistently is not. Context lives in GitHub (READMEs, commits, releases), and turning it into a good LinkedIn post takes time, so most projects never get posted about.

## 2. Goal
An agent that reads my GitHub + project context, drafts complete LinkedIn posts, and publishes **only after I explicitly approve**.

## 3. Non-Goals (v1)
- Auto-posting without approval (never)
- Comments, DMs, connection requests, engagement automation
- Multi-account / team support
- Analytics dashboard
- Image generation (v2)

## 4. User
Single user (Naman): developer, builds frontend / backend / mobile projects, wants a visible build-in-public presence.

## 5. User Stories
| ID | Story |
|----|-------|
| U1 | As a user, I point the agent at a repo and get a ready-to-post draft. |
| U2 | As a user, I get 2–3 variants with different hooks. |
| U3 | As a user, I can approve, edit, regenerate, or skip a draft. |
| U4 | As a user, nothing is posted unless I approved that exact text. |
| U5 | As a user, the agent never reposts a project/commit it already covered. |
| U6 | As a user, the agent suggests which repo to post about next. |
| U7 | As a user, I'm notified when the LinkedIn token is about to expire. |

## 6. Functional Requirements
**FR-1 Ingest**
- Fetch repos via GitHub API (public + optionally private by token scope).
- Per repo: name, description, README, languages, topics, stars, last push, recent commits, releases, homepage URL.
- Optional: local `projects/*.md` files for extra context (goals, challenges, learnings).

**FR-2 Select**
- Manual: `--repo <name>`.
- Auto: rank by recent activity × not-yet-posted × has README.

**FR-3 Draft**
- Generate full post: hook, problem, what I built, stack, key learning/challenge, CTA, hashtags.
- Follow `profile.yaml` (tone, banned phrases, hashtags, length).
- 2–3 variants per run.
- Only claims grounded in fetched context (no invented metrics/users/results).

**FR-4 Approve**
- Present draft via CLI (MVP) → Telegram (v1.1).
- Actions: Approve / Edit / Regenerate (with optional instruction) / Skip.
- Approval is bound to a content hash; any edit invalidates prior approval.

**FR-5 Publish**
- Post to LinkedIn via official API (`w_member_social`).
- Store resulting post URN/URL.

**FR-6 Memory/State**
- Track: repos posted, commit SHAs covered, drafts, approvals, post URNs.

**FR-7 Safety**
- `--dry-run` mode (default ON until explicitly disabled).
- Audit log of every draft, decision, and publish call.

## 7. Non-Functional Requirements
- **Safety:** zero publish path without a valid approval record.
- **Security:** secrets only in env / OS keychain; never logged or committed.
- **Cost:** < $0.10 per draft run.
- **Latency:** draft in < 30s.
- **Reliability:** idempotent publish (no double posts on retry).
- **Portability:** runs locally; optional GitHub Actions / cron for scheduled drafting.

## 8. Success Metrics
- ≥ 80% of drafts approved with ≤ 1 edit after 2 weeks of tuning.
- 0 unapproved posts. 0 duplicate posts.
- ≥ 1 post/week sustained for 8 weeks.

## 9. Constraints & Assumptions
- LinkedIn API access via self-serve developer app ("Share on LinkedIn" + "Sign In with LinkedIn using OpenID Connect").
- Access tokens expire (~60 days); self-serve apps typically don't get refresh tokens → plan for periodic re-auth.
- Post text limit ~3,000 chars.
- LinkedIn API version header is date-based and must be kept current.

## 10. Risks
| Risk | Mitigation |
|------|-----------|
| LLM hallucinates facts | Grounding rule + "claims check" pass listing each claim's source |
| Token expiry silently breaks posting | Expiry tracking + alert 7 days prior |
| LinkedIn API / policy change | Isolate in `publisher/linkedin.py`; clipboard-copy fallback |
| Generic "AI-sounding" posts | Style profile, banned phrases, few-shot of my own past posts |
| Leaking private repo details | Private repos opt-in per repo; redaction check before draft |

## 11. Milestones
M1 CLI draft → M2 approval loop → M3 LinkedIn publish → M4 Telegram + scheduling. See `IMPLEMENTATION_PLAN.md`.

## 12. Open Questions
- LLM provider default: Claude or Gemini? (abstraction supports both)
- Include private repos? Which?
- Post cadence target (weekly?)
- Add images/screenshots in v2?
