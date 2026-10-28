# ARCHITECTURE — LinkedIn Post Agent

## 1. Overview
Pipeline with a hard human approval gate. Single-user, local-first Python app.

```
            ┌────────────┐   ┌───────────────┐   ┌──────────────┐
 GitHub ───▶│ Ingestor   │──▶│ Context       │──▶│ Drafter      │
 local md ─▶│ (github.py)│   │ Builder       │   │ (LLM)        │
            └────────────┘   └───────────────┘   └──────┬───────┘
                                    ▲                    │ drafts[]
                                    │                    ▼
                             ┌──────┴──────┐      ┌──────────────┐
                             │ State (SQLite)│◀───│ Claims Check │
                             └──────┬──────┘      └──────┬───────┘
                                    │                    ▼
                                    │             ┌──────────────┐  edit/regen
                                    │             │ Approval Gate│◀────────┐
                                    │             │ CLI/Telegram │─────────┘
                                    │             └──────┬───────┘
                                    │                    │ approved(hash)
                                    ▼                    ▼
                             ┌─────────────┐      ┌──────────────┐
                             │ Audit Log   │◀─────│ Publisher    │──▶ LinkedIn API
                             └─────────────┘      └──────────────┘
```

## 2. Components
| Module | Responsibility |
|--------|----------------|
| `ingest/github.py` | Fetch repo metadata, README, commits, releases |
| `ingest/local.py` | Read optional `projects/*.md` notes |
| `context/builder.py` | Merge sources → `ProjectContext`; trim to token budget |
| `context/selector.py` | Rank/pick repo to post about |
| `llm/base.py` | `LLMClient` interface (`complete(system, user) -> str`) |
| `llm/claude.py`, `llm/gemini.py` | Provider implementations |
| `drafter/drafter.py` | Prompt assembly (uses `SKILL.md` + `profile.yaml`), variants |
| `drafter/claims_check.py` | Second LLM pass: list each claim + source line; flag unsupported |
| `approval/gate.py` | State machine, content-hash binding |
| `approval/cli.py`, `approval/telegram.py` | Approval UIs (same interface) |
| `publisher/linkedin.py` | OAuth, token store, `create_post()` |
| `store/db.py` | SQLite: posts, drafts, approvals, tokens meta |
| `audit/log.py` | Append-only JSONL log |
| `cli.py` | Typer entrypoint |

## 3. Data Models (pydantic)
```python
ProjectContext: repo, description, readme_excerpt, languages[], topics[],
                recent_commits[{sha,msg,date}], releases[], homepage, stars,
                local_notes, last_push

Draft: id, repo, variant_no, text, text_sha256, claims[{claim, source}],
       status, created_at, parent_draft_id?

Approval: draft_id, text_sha256, approved_at, channel   # bound to exact text

Post: draft_id, linkedin_urn, url, posted_at, idempotency_key
```

## 4. Draft State Machine
```
CREATED → CHECKED → PENDING_APPROVAL ─┬─▶ APPROVED → PUBLISHED
                                      ├─▶ EDITED → (new hash) PENDING_APPROVAL
                                      ├─▶ REGENERATED → new Draft (CREATED)
                                      └─▶ SKIPPED
APPROVED → FAILED (publish error, retryable, same idempotency key)
```
Rules: only `APPROVED` with matching `text_sha256` may reach the Publisher. Any text mutation creates a new hash and resets to `PENDING_APPROVAL`.

## 5. Publish Flow (LinkedIn)
1. OAuth 2.0 authorization-code flow (one-time, local redirect `http://localhost:8080/callback`).
2. Scopes: `openid profile w_member_social`.
3. Get member id from `/v2/userinfo` (`sub`) → author URN `urn:li:person:{sub}`.
4. `POST https://api.linkedin.com/rest/posts`
   - Headers: `Authorization: Bearer …`, `Linkedin-Version: YYYYMM` (config), `X-Restli-Protocol-Version: 2.0.0`
   - Body: `author`, `commentary`, `visibility: PUBLIC`, `distribution.feedDistribution: MAIN_FEED`, `lifecycleState: PUBLISHED`
5. Read post URN from `x-restli-id` response header; persist.
6. Token expiry stored; warn at T-7 days.

> Verify current endpoints/versions in LinkedIn's official docs before implementing; they change.

## 6. Configuration
| File | Contents |
|------|----------|
| `.env` | `GITHUB_TOKEN`, `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LINKEDIN_CLIENT_ID/SECRET`, `LINKEDIN_VERSION`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `DRY_RUN=true` |
| `profile.yaml` | name, tone, audience, hashtags, banned phrases, length range, CTA styles, example past posts |
| `config.yaml` | repo allowlist/denylist, private-repo opt-in, selection weights |

## 7. Security
- Secrets from env/keychain only; `.env` git-ignored; never logged.
- GitHub token: fine-grained, read-only (`Contents`, `Metadata`).
- Redaction pass before LLM call: strip keys/tokens/emails detected in README/commits.
- Telegram: accept updates only from `TELEGRAM_CHAT_ID`.
- `DRY_RUN=true` default: publisher logs the payload instead of sending.

## 8. Error Handling
| Failure | Behavior |
|---------|----------|
| GitHub rate limit | Backoff, use cache (ETag) |
| LLM error / malformed output | Retry ×2, then abort run with log |
| Claims check flags unsupported claim | Auto-regenerate once; else show warning in approval UI |
| LinkedIn 401 | Mark token expired, notify, no retry |
| LinkedIn 5xx / timeout | Retry with same idempotency key; check for existing post before re-send |

## 9. Repo Layout
```
linkedin-agent/
├── src/linkedin_agent/{ingest,context,llm,drafter,approval,publisher,store,audit}/
├── src/linkedin_agent/cli.py
├── tests/
├── projects/            # optional local notes
├── profile.yaml
├── config.yaml
├── .env.example
├── pyproject.toml
└── docs: PRD.md ARCHITECTURE.md IMPLEMENTATION_PLAN.md RULES.md SKILL.md GEMINI.md
```

## 10. Tech Stack
Python 3.11+, `httpx`, `pydantic`, `typer`, `PyGithub` (or raw REST), `python-telegram-bot`, `sqlite3`, `pytest`, `ruff`, `mypy`. Scheduling: cron / GitHub Actions.
