# LinkedIn Post Agent

A local-first Python CLI agent that reads your GitHub repositories and project notes, drafts high-signal LinkedIn posts, and publishes **only after your explicit human approval**.

---

## Key Features

- **Hard Cryptographic Approval Gate:** No post can ever be published without a matching database `Approval` record bound to the exact content hash (`text_sha256`). Any edit immediately invalidates prior approval.
- **Default Dry Run:** `DRY_RUN=true` is enabled by default to prevent accidental live broadcasts.
- **Strict Grounding:** Every claim in generated drafts cites its factual source (README, commit SHA, or local note). Invented metrics and buzzwords are detected and flagged.
- **Multi-Angle Drafting:** Generates 2–3 variants per repository (Problem $\rightarrow$ Solution, Technical Challenge, Lesson Learned) matching your voice from `profile.yaml`.
- **Intelligent Suggestion Engine:** Ranks repositories by push recency, content quality, and unposted status to suggest what to feature next.
- **Omni-Channel Approval:** Review and approve drafts via interactive terminal CLI or mobile Telegram bot with inline action buttons.

---

## Architecture

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

---

## Installation & Setup

### 1. Prerequisites
- Python 3.11+
- Git

### 2. Install Package
```bash
git clone <repo_url>
cd AIAGENT
pip install -e ".[dev]"
```

### 3. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate the values in `.env`:
```env
GITHUB_TOKEN=ghp_...
LLM_PROVIDER=gemini        # or claude
LLM_API_KEY=your_key_here
LLM_MODEL=gemini-1.5-pro    # or claude-3-5-sonnet-20241022
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
LINKEDIN_REDIRECT_URI=http://localhost:8080/callback
LINKEDIN_VERSION=202401
TELEGRAM_BOT_TOKEN=...      # optional
TELEGRAM_CHAT_ID=...        # optional
DRY_RUN=true
```

---

## External Credentials Setup

### LinkedIn Developer App
1. Go to the [LinkedIn Developer Portal](https://www.linkedin.com/developers/).
2. Create a new App and associate it with your LinkedIn Page.
3. Under the **Products** tab, add:
   - **Share on LinkedIn** (provides `w_member_social`)
   - **Sign In with LinkedIn using OpenID Connect** (provides `openid profile`)
4. Under the **Auth** tab, add `http://localhost:8080/callback` to **Authorized redirect URLs for your app**.
5. Copy your **Client ID** and **Client Secret** into your `.env` file.
6. Authenticate once via CLI:
   ```bash
   agent auth login
   ```

### GitHub Personal Access Token
1. Go to **GitHub Settings $\rightarrow$ Developer settings $\rightarrow$ Personal access tokens $\rightarrow$ Fine-grained tokens**.
2. Generate a token with read-only permissions:
   - `Repository permissions: Contents (Read-only)`
   - `Repository permissions: Metadata (Read-only)`
3. Save to `GITHUB_TOKEN` in your `.env`.

---

## CLI Usage

### Check Authentication Status
```bash
agent auth status
```
Displays GitHub connection, LinkedIn token validity, and warns if your LinkedIn token is within 7 days of expiry.

### Suggest What to Post About Next
```bash
agent suggest --limit 5
```
Inspects your repositories and ranks them by activity recency and unposted history.

### Inspect Repository Context
```bash
agent context --repo <owner/repo>
```
Fetches repository metadata, README excerpt, commit history, and local project notes from `projects/<repo>.md` with sensitive tokens and emails automatically redacted.

### Generate Drafts
```bash
agent draft --repo <owner/repo>
```
Generates 2–3 grounded variants with cited claims and warnings for unsupported assertions.

### Run Full Approval & Publish Pipeline
```bash
# Safe dry-run (default)
agent run --repo <owner/repo> --dry-run

# Live publication (strictly gated on explicit approval)
agent run --repo <owner/repo> --no-dry-run
```

---

## Verification & Quality Gates

Run the test suite, style linter, and static type checker:
```bash
# Run unit & hardening test suite
pytest -q

# Format & lint check
ruff check .

# Strict type check
mypy src
```
