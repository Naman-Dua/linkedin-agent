# IMPLEMENTATION PLAN — LinkedIn Post Agent

Rule: finish + test each phase before the next. Each phase ends with a runnable command.

## Phase 0 — Setup (0.5 day)
- [ ] Repo + `pyproject.toml`, `ruff`, `mypy`, `pytest`
- [ ] `.env.example`, `.gitignore` (`.env`, `*.db`, `tokens*`)
- [ ] `profile.yaml` + `config.yaml` skeletons
- [ ] Register LinkedIn developer app (add "Share on LinkedIn" + "Sign In with LinkedIn using OpenID Connect")
- [ ] Create fine-grained GitHub PAT (read-only)

**Done when:** `python -m linkedin_agent --help` works.

## Phase 1 — Ingest + Context (1 day)
- [ ] `ingest/github.py`: list repos, fetch README, languages, commits, releases
- [ ] ETag caching
- [ ] `ingest/local.py`: read `projects/*.md`
- [ ] `context/builder.py`: `ProjectContext` + token-budget trimming
- [ ] Redaction pass (secrets/emails)
- [ ] Tests with recorded fixtures

**Done when:** `agent context --repo <name>` prints clean summary.

## Phase 2 — Drafter (1 day)
- [ ] `llm/base.py` + one provider (Claude or Gemini)
- [ ] Prompt assembly from `SKILL.md` + `profile.yaml` + `ProjectContext`
- [ ] Structured output (JSON: variants[], each with text + claims[])
- [ ] `claims_check.py`
- [ ] 2–3 variants, length/hashtag validation

**Done when:** `agent draft --repo <name>` prints 3 grounded drafts.

## Phase 3 — State + Approval (1 day)
- [ ] SQLite schema (drafts, approvals, posts)
- [ ] State machine + content-hash binding
- [ ] CLI approval UI: approve / edit (`$EDITOR`) / regenerate / skip
- [ ] Audit log (JSONL)
- [ ] Tests: edit invalidates approval; no path to publish without approval

**Done when:** `agent run --repo <name> --dry-run` completes the loop, logging payload only.

## Phase 4 — LinkedIn Publisher (1 day)
- [ ] OAuth local-callback flow, token storage (keychain/encrypted file)
- [ ] `/v2/userinfo` → author URN
- [ ] `create_post()` via Posts API
- [ ] Idempotency key + duplicate check
- [ ] Token expiry tracking + `agent auth status`
- [ ] Manual test with `visibility: CONNECTIONS` first (if supported), then PUBLIC

**Done when:** one real approved post appears on profile; URN stored.

## Phase 5 — Selection + Scheduling (0.5–1 day)
- [ ] `context/selector.py`: rank repos (activity × unposted × README quality)
- [ ] `agent suggest` command
- [ ] Cron / GitHub Actions weekly: generate drafts only → notify
- [ ] Posted-history guard (no repeat repos/commits)

## Phase 6 — Telegram Approval (1 day)
- [ ] Bot with inline buttons (Approve/Edit/Regenerate/Skip)
- [ ] Chat-id allowlist
- [ ] Edit flow via reply message
- [ ] Expiry alerts (token T-7d)

## Phase 7 — Hardening (ongoing)
- [ ] Few-shot from my past posts to tune voice
- [ ] Error/backoff paths tested
- [ ] README + setup guide
- [ ] v2 ideas: screenshots/GIFs, carousel PDF, post performance feedback loop

## Test Checklist (must pass before disabling DRY_RUN)
- [ ] Publish blocked without approval
- [ ] Publish blocked after edit until re-approved
- [ ] Retry doesn't double-post
- [ ] Secrets never appear in logs
- [ ] Unsupported claims are flagged
- [ ] Expired token → clear error, no crash

## Suggested Timeline
~6–7 working days to Phase 5; Telegram adds 1 day.
