# GEMINI.md — Project Context for Gemini CLI

## Project
**LinkedIn Post Agent** — Python CLI agent that reads my GitHub repos + project notes, drafts LinkedIn posts, and publishes **only after my explicit approval**.

## Read first (source of truth)
@./PRD.md
@./ARCHITECTURE.md
@./IMPLEMENTATION_PLAN.md
@./RULES.md
@./SKILL.md

## Non-negotiables
1. No code path may publish without a matching `Approval` (same `text_sha256`).
2. `DRY_RUN=true` by default.
3. Never log or commit secrets. Never hardcode keys.
4. Drafts contain only claims grounded in fetched context.

## Stack
Python 3.11+, httpx, pydantic, typer, SQLite, python-telegram-bot, pytest, ruff, mypy.

## Commands
```bash
pip install -e ".[dev]"
pytest -q
ruff check . && mypy src
agent context --repo <name>
agent draft --repo <name>
agent run --repo <name> --dry-run
agent auth status
```

## Working Style
- Follow `IMPLEMENTATION_PLAN.md` phase by phase; don't skip ahead.
- Before coding a phase: restate its tasks and acceptance criteria in 3–5 lines.
- Small commits (Conventional Commits). Tests with each module.
- Ask only when blocked; otherwise state assumptions and continue.
- Keep output terse: code + minimal explanation.
- If a LinkedIn API detail is uncertain, check the official docs; don't guess endpoints/versions.

## Layout
```
src/linkedin_agent/{ingest,context,llm,drafter,approval,publisher,store,audit}/
```

## Current Phase
Phase 4 → LinkedIn Publisher
