# Implementation Plan: LinkedIn Post Agent

## Overview
A local-first Python CLI agent that monitors GitHub repositories and project notes to draft high-signal LinkedIn posts, publishing **strictly after explicit human approval** via a cryptographic content-hash approval gate (`text_sha256`). `DRY_RUN` is enabled by default, and all drafted claims must be verifiably grounded in fetched context.

## Architecture Decisions
- **Strict Approval Gate:** The publisher accepts only drafts with a valid `Approval` record matching the SHA-256 hash of the exact post text. Any text change requires re-approval.
- **Dry Run by Default:** `DRY_RUN=true` prevents accidental live posts until explicitly bypassed by the user.
- **Two-Pass Generation:** 
  1. Drafter generates 2–3 variants with distinct angles using `SKILL.md` and `profile.yaml`.
  2. Claims Check pass verifies every statement against context facts, tagging sources and flagging hallucinated or unsupported claims.
- **Modular Architecture:** Pure domain logic separated from side-effects (GitHub API, LLM API, SQLite, LinkedIn REST API).
- **Tooling & Type Safety:** Python 3.11+, typed end-to-end with `mypy --strict`, formatted/linted via `ruff`, tested via `pytest`.

---

## Phase Breakdown & Dependencies

```
Phase 0: Setup & Scaffolding
    │
    ▼
Phase 1: Ingest + Context Builder (GitHub, Local Notes, Redaction)
    │
    ▼
Phase 2: LLM Drafter & Claims Checker (Skill Prompts, Grounding Validation)
    │
    ▼
Phase 3: SQLite Store & CLI Approval Gate (Content-Hash State Machine, Audit Log)
    │
    ▼
Phase 4: LinkedIn Publisher (OAuth 2.0, Posts API, Idempotency)
    │
    ▼
Phase 5: Repo Selector & Scheduling (Ranking Engine, Suggested Repos)
    │
    ▼
Phase 6: Telegram Bot Approval UI (Inline Keyboards, Expiry Alerts)
    │
    ▼
Phase 7: Hardening & Voice Tuning
```

---

## Detailed Task Breakdown

### Phase 0: Setup & Scaffolding
- **Task 0.1:** Git repository initialization and `.gitignore` (`.env`, `*.db`, `tokens*`, cache directories, test artifacts).
- **Task 0.2:** `pyproject.toml` with dependencies (`httpx`, `pydantic>=2.0`, `typer>=0.9.0`, `pyyaml`, `python-telegram-bot>=20.0`, dev tools `pytest`, `ruff`, `mypy`) and tool configurations.
- **Task 0.3:** Configuration skeletons: `.env.example`, `profile.yaml` (style, audience, banned words, hashtags), and `config.yaml` (repo allowlist/denylist, private repo flags).
- **Task 0.4:** Package layout under `src/linkedin_agent/` with entrypoints (`cli.py`, `__main__.py`) and initial smoke test.
- **Checkpoint 0:** `python -m linkedin_agent --help` succeeds; `ruff check .` and `mypy src` pass.

### Phase 1: Ingest & Context Builder
- **Task 1.1:** `ingest/github.py` REST client with ETag caching, rate-limit backoff, fetching repo metadata, README, languages, recent commits, and releases.
- **Task 1.2:** `ingest/local.py` for optional project notes (`projects/*.md`).
- **Task 1.3:** `context/builder.py` constructing `ProjectContext` with token-budget trimming.
- **Task 1.4:** Security redaction pass stripping secrets, API keys, and email addresses before context leaves the boundary.
- **Task 1.5:** Unit tests with recorded fixture data for ingest and context assembly.
- **Checkpoint 1:** `agent context --repo <name>` outputs clean, sanitized context.

### Phase 2: Drafter & Grounding Checker
- **Task 2.1:** `llm/base.py` interface and provider implementation (`llm/gemini.py` / `llm/claude.py`).
- **Task 2.2:** `drafter/drafter.py` prompt assembly integrating `SKILL.md`, `profile.yaml`, and `ProjectContext` to produce 2–3 hook/angle variants in structured JSON.
- **Task 2.3:** `drafter/claims_check.py` 2nd-pass verifier matching claims against source text.
- **Task 2.4:** Unit tests for drafting and claims validation with mocked LLM responses.
- **Checkpoint 2:** `agent draft --repo <name>` returns 2–3 grounded variants with cited claims.

### Phase 3: SQLite Store, State Machine & CLI Approval Gate
- **Task 3.1:** SQLite schema and migration in `store/db.py` for drafts, approvals, posts, and token metadata.
- **Task 3.2:** State machine and cryptographic `text_sha256` content-hash binding in `approval/gate.py`.
- **Task 3.3:** Append-only JSONL audit logging in `audit/log.py`.
- **Task 3.4:** Interactive CLI approval interface (`approval/cli.py`) supporting Approve, Edit (`$EDITOR`), Regenerate, and Skip.
- **Task 3.5:** Invariant tests: any text edit invalidates approval; publisher rejects unapproved hashes.
- **Checkpoint 3:** `agent run --repo <name> --dry-run` executes the full approval cycle and safely logs payload.

### Phase 4: LinkedIn Publisher
- **Task 4.1:** OAuth 2.0 authorization code flow with local redirect server in `publisher/linkedin.py`.
- **Task 4.2:** Member URN resolution via `/v2/userinfo` and secure token storage.
- **Task 4.3:** `create_post()` implementation calling `POST https://api.linkedin.com/rest/posts` with version headers, idempotency keys, and error handling.
- **Task 4.4:** Token expiration monitor and `agent auth status` command.
- **Checkpoint 4:** End-to-end publish test with real/dry-run response storing LinkedIn URN.

### Phase 5: Selection Engine & Scheduled Drafting
- **Task 5.1:** `context/selector.py` ranking repos by activity, README quality, and unposted status.
- **Task 5.2:** `agent suggest` CLI command.
- **Task 5.3:** Repost guard ensuring already-covered commit SHAs and repos are skipped.
- **Checkpoint 5:** Auto-selection reliably surfaces top unposted repo.

### Phase 6: Telegram Bot Approval UI
- **Task 6.1:** `approval/telegram.py` bot with inline buttons for Approve, Edit, Regenerate, Skip.
- **Task 6.2:** Chat ID whitelist restriction and message-reply edit handler.
- **Task 6.3:** Automated token expiration warning notifications.
- **Checkpoint 6:** Mobile approval cycle completes via Telegram.

### Phase 7: Hardening & Voice Tuning
- **Task 7.1:** Integration of user's past post examples into `profile.yaml` few-shot prompts.
- **Task 7.2:** End-to-end failure mode testing (network timeouts, rate limits, expired tokens).
- **Task 7.3:** Setup documentation and user manual.
- **Checkpoint 7:** All acceptance criteria in `RULES.md` and `PRD.md` verified.

---

## Risks & Mitigations
| Risk | Severity | Mitigation |
| :--- | :--- | :--- |
| LLM invents metrics or facts | High | Dedicated claims-checking pass cites source line for every factual statement; unverified claims abort or warn. |
| Accidental unapproved post | Critical | Publisher strictly validates database `Approval` record with matching `text_sha256`. `DRY_RUN=true` default. |
| Private repo secrets leaked | High | Private repos are opt-in only; automated regex redaction pass scrubs credentials and emails prior to prompt construction. |
| LinkedIn API changes / breaks | Medium | LinkedIn API logic isolated in `publisher/linkedin.py`; clipboard fallback if API is unreachable. |
