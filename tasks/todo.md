# Tasks: LinkedIn Post Agent

## Phase 0: Setup & Scaffolding

- [ ] **Task 0.1: Initialize Git and Ignore Rules**
  - **Description:** Initialize git repo and configure `.gitignore` for `.env`, `*.db`, `tokens*`, cache and build files.
  - **Acceptance criteria:**
    - Git repository initialized.
    - `.gitignore` ignores `.env`, `*.db`, `tokens*`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `__pycache__`.
  - **Verification:** `git status` shows clean tracking; ignored files are ignored.

- [ ] **Task 0.2: Project Dependencies & Tooling Configuration**
  - **Description:** Create `pyproject.toml` with dependencies (`httpx`, `pydantic>=2.0`, `typer>=0.9.0`, `pyyaml`, `python-telegram-bot>=20.0`, `pytest`, `ruff`, `mypy`) and tool configurations.
  - **Acceptance criteria:**
    - `pyproject.toml` defines package metadata, scripts entrypoint `agent = "linkedin_agent.cli:app"`.
    - Strict `mypy` and `ruff` rules configured according to `RULES.md`.
  - **Verification:** `pip install -e .[dev]` installs cleanly.

- [ ] **Task 0.3: Configuration Templates and Skeletons**
  - **Description:** Create `.env.example`, `profile.yaml`, and `config.yaml` skeletons.
  - **Acceptance criteria:**
    - `.env.example` lists all required environment variables with comments.
    - `profile.yaml` contains voice settings, banned words, CTA styles, length constraints.
    - `config.yaml` defines repo selection filters, allowlist/denylist, and private repo settings.
  - **Verification:** Files exist and are valid YAML / env format.

- [ ] **Task 0.4: Package Scaffolding & Initial Entrypoint**
  - **Description:** Create `src/linkedin_agent/` module structure with `cli.py`, `__init__.py`, `__main__.py`, and initial tests.
  - **Acceptance criteria:**
    - Modules `ingest`, `context`, `llm`, `drafter`, `approval`, `publisher`, `store`, `audit` exist with `__init__.py`.
    - `cli.py` has Typer app with `context`, `draft`, `run`, `auth` command placeholders.
  - **Verification:** `python -m linkedin_agent --help` outputs help menu; `pytest` passes initial test.

- [ ] **Checkpoint 0: Phase 0 Completion**
  - [ ] `python -m linkedin_agent --help` succeeds
  - [ ] `ruff check .` passes
  - [ ] `mypy src` passes
  - [ ] Update `GEMINI.md` current phase to Phase 1

---

## Phase 1: Ingest & Context Builder

- [ ] **Task 1.1: GitHub Ingest Module**
  - **Description:** Implement `ingest/github.py` using `httpx` to fetch repo metadata, README, languages, commits, and releases with ETag caching.
- [ ] **Task 1.2: Local Notes Ingest**
  - **Description:** Implement `ingest/local.py` to parse optional notes in `projects/*.md`.
- [ ] **Task 1.3: Redaction Pass**
  - **Description:** Implement regex security redaction for keys, tokens, emails in `context/redaction.py`.
- [ ] **Task 1.4: Context Assembly**
  - **Description:** Implement `context/builder.py` assembling `ProjectContext` and trimming to token budget.
- [ ] **Task 1.5: Ingest & Context Tests**
  - **Description:** Write unit tests with recorded fixtures for all Phase 1 components.
- [ ] **Checkpoint 1: Phase 1 Verification**
  - [ ] `agent context --repo <name>` prints clean summary
  - [ ] All tests pass; linters clean

---

## Phase 2: Drafter & Claims Checking

- [ ] **Task 2.1: LLM Client Interface & Providers**
  - **Description:** Create `llm/base.py` interface and Gemini/Claude implementation.
- [ ] **Task 2.2: Drafter Prompt & Generation**
  - **Description:** Create `drafter/drafter.py` assembling prompt from `SKILL.md` + `profile.yaml` + context to produce structured JSON variants.
- [ ] **Task 2.3: Claims Checking Pass**
  - **Description:** Create `drafter/claims_check.py` to verify grounded facts and flag unsupported claims.
- [ ] **Task 2.4: Drafter Unit Tests**
  - **Description:** Test variant generation and claims validation with mock responses.
- [ ] **Checkpoint 2: Phase 2 Verification**
  - [ ] `agent draft --repo <name>` outputs 2–3 grounded variants with cited claims
  - [ ] All tests pass; linters clean

---

## Phase 3: State & CLI Approval Gate

- [ ] **Task 3.1: SQLite Database Storage**
  - **Description:** Implement schema in `store/db.py` for drafts, approvals, posts.
- [ ] **Task 3.2: Approval State Machine & Content Hash**
  - **Description:** Implement `approval/gate.py` enforcing `text_sha256` binding.
- [ ] **Task 3.3: CLI Approval UI & JSONL Audit Log**
  - **Description:** Implement interactive CLI approval loop in `approval/cli.py` and audit logger in `audit/log.py`.
- [ ] **Task 3.4: Approval Invariant Tests**
  - **Description:** Test that edits reset approval and unapproved text cannot proceed.
- [ ] **Checkpoint 3: Phase 3 Verification**
  - [ ] `agent run --repo <name> --dry-run` completes loop and logs payload
  - [ ] All tests pass; linters clean

---

## Phase 4: LinkedIn Publisher

- [ ] **Task 4.1: OAuth 2.0 Flow & Token Storage**
  - **Description:** Implement local OAuth callback server and token persistence in `publisher/linkedin.py`.
- [ ] **Task 4.2: LinkedIn Posts API Client**
  - **Description:** Implement `create_post()` with idempotency key, REST API headers, and error handling.
- [ ] **Task 4.3: Auth Status & Expiry Monitoring**
  - **Description:** Implement `agent auth status` and expiry calculations.
- [ ] **Checkpoint 4: Phase 4 Verification**
  - [ ] Real or mock post creates post and records URN
  - [ ] All tests pass; linters clean

---

## Phase 5: Selection & Scheduling

- [ ] **Task 5.1: Repo Ranking Engine**
  - **Description:** Implement `context/selector.py` scoring repos based on activity, unposted status, and README.
- [ ] **Task 5.2: `agent suggest` Command**
  - **Description:** CLI command suggesting the next repo to post about.
- [ ] **Task 5.3: Repost Prevention Guards**
  - **Description:** Prevent duplicate posts for previously covered repos/commits.
- [ ] **Checkpoint 5: Phase 5 Verification**
  - [ ] `agent suggest` accurately ranks repositories

---

## Phase 6: Telegram Approval UI

- [ ] **Task 6.1: Telegram Bot Integration**
  - **Description:** Implement `approval/telegram.py` with inline buttons for draft approval/editing/skipping.
- [ ] **Task 6.2: Whitelist & Alerts**
  - **Description:** Strict chat ID checking and token expiration alerts.
- [ ] **Checkpoint 6: Phase 6 Verification**
  - [ ] Interactive approval loop verified over Telegram

---

## Phase 7: Hardening & Voice Tuning

- [ ] **Task 7.1: Few-Shot Profiles**
  - **Description:** Tune prompt with user's past post examples.
- [ ] **Task 7.2: Resilience & Network Error Tests**
  - **Description:** Test rate limiting, 401 handling, and idempotency recovery.
- [ ] **Checkpoint 7: Ready for Production**
  - [ ] All tests pass, DRY_RUN test checklist verified
