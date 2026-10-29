# LinkedIn Post Agent

A local-first Python CLI agent that reads your GitHub repositories and project notes, drafts high-signal engineering posts, and publishes **only after your explicit human approval**.

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

### 2. Clone & Install Package
```bash
git clone https://github.com/Naman-Dua/linkedin-agent.git
cd linkedin-agent
pip install -e ".[dev]"
```

### 3. Create Environment File
Copy `.env.example` to `.env`:
```bash
# On Windows (PowerShell):
Copy-Item .env.example .env

# On macOS/Linux:
cp .env.example .env
```

---

## Step-by-Step API Keys & Credentials Guide

Follow these steps to acquire each credential for your `.env` file:

### 1. Google Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Click **"Create API Key"** (or select an existing project).
3. Copy your API key (starts with `AIzaSy...`).
4. In `.env`, configure:
   ```ini
   LLM_PROVIDER=gemini
   LLM_API_KEY=AIzaSy...your_key_here
   LLM_MODEL=gemini-3.5-flash
   ```
   *(Note: Model names must be lowercase. `gemini-3.5-flash` is fast and recommended).*

---

### 2. GitHub Personal Access Token
A token is recommended to fetch your commit history and repository metadata without hitting public rate limits:
1. Go to [GitHub Settings $\rightarrow$ Developer settings $\rightarrow$ Fine-grained tokens](https://github.com/settings/tokens?type=beta).
2. Click **"Generate new token"**.
3. Name it (e.g., `linkedin-agent`).
4. Set **Repository access** to `All repositories` (or select specific ones).
5. Under **Permissions** $\rightarrow$ **Repository permissions**:
   - **Contents:** `Read-only`
   - **Metadata:** `Read-only`
6. Click **Generate token** and copy the token (starts with `github_pat_...`).
7. In `.env`, set:
   ```ini
   GITHUB_TOKEN=github_pat_...your_token_here
   ```

---

### 3. LinkedIn Developer App & OAuth Setup

LinkedIn requires a verified developer application to publish posts to your profile:

#### A. Create a Company Page (Prerequisite)
LinkedIn requires you to link a company page where you are an admin. Do **not** use your university or workplace page unless you are a Super Admin.
1. Open [LinkedIn Company Setup](https://www.linkedin.com/company/setup/new/).
2. Select **Company**.
3. Name it after your personal brand (e.g., `Naman Projects` or `YourName Dev`).
4. Choose any industry (e.g. *Software Development*) and size (`0-1 employees`).
5. Click **Create page**. You are now instantly a Super Admin.

#### B. Create the Developer App
1. Go to the [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps/new).
2. Fill in:
   - **App name:** e.g., `My LinkedIn Agent`
   - **LinkedIn Page:** Type the name of the company page you created in Step A and select it from the dropdown.
   - **App logo:** Upload any square icon/logo.
3. Check the legal agreement box and click **Create app**.

#### C. Request API Permissions (Products)
1. In your app dashboard, go to the **Products** tab.
2. Find **Share on LinkedIn** $\rightarrow$ click **Request access** (grants `w_member_social`).
3. Find **Sign In with LinkedIn using OpenID Connect** $\rightarrow$ click **Request access** (grants `openid` and `profile`).
*(Both activate instantly).*

#### D. Set Authorized Redirect URI
1. Click the **Auth** tab.
2. Under **OAuth 2.0 settings** $\rightarrow$ **Authorized redirect URLs for your app**, click **Add redirect URL**.
3. Enter exactly:
   ```text
   http://localhost:8080/callback
   ```
4. Click **Update**.
5. Copy your **Client ID** and **Client Secret** into `.env`:
   ```ini
   LINKEDIN_CLIENT_ID=your_client_id_here
   LINKEDIN_CLIENT_SECRET=your_client_secret_here
   LINKEDIN_REDIRECT_URI=http://localhost:8080/callback
   LINKEDIN_VERSION=202601
   ```

---

### 4. Telegram Approval Bot (Optional — For Mobile Approvals)
If you want to review and approve drafts from your phone via inline buttons:
1. In Telegram, search for `@BotFather` and send `/newbot`.
2. Follow prompts to name your bot (e.g., `naman_post_bot`).
3. Copy the **HTTP API token** BotFather gives you into `TELEGRAM_BOT_TOKEN`.
4. In Telegram, search for `@userinfobot`, press **Start**, and copy your numeric ID into `TELEGRAM_CHAT_ID`.
5. Open your new bot's chat and press **Start** so it can message you.

---

## How to Use: Complete Walkthrough

### Step 1: Verify Authentication & Tokens
Check that your GitHub and LinkedIn credentials are active:
```bash
agent auth status
```
If LinkedIn is not yet authenticated, run the one-time browser login:
```bash
agent auth login
```
*Your browser opens $\rightarrow$ click **Allow** $\rightarrow$ your access token is securely saved in your local SQLite database.*

---

### Step 2: Discover What to Post About
Rank all your GitHub repositories by push recency, unposted status, and documentation quality:
```bash
agent suggest --limit 5
```
Example output:
```text
=== Suggested Repositories for Next Post ===
#1 [0.92] Naman-Dua/linkedin-agent
    ★ Not yet posted, pushed 0d ago, has description
#2 [0.74] Naman-Dua/multimodal-attendance-engagement-agent
    ★ Not yet posted, pushed 8d ago
```

---

### Step 3: Inspect Ingested Context & Redaction
Preview the factual context extracted from the repo (commits, README, languages) with secrets automatically masked:
```bash
agent context --repo Naman-Dua/multimodal-attendance-engagement-agent
```

---

### Step 4: Run Safe Dry-Run Approval Flow
Run the full drafting and approval pipeline safely in your terminal without posting:
```bash
agent run --repo Naman-Dua/multimodal-attendance-engagement-agent --dry-run
```
1. The LLM generates 3 distinct grounded variants matching your voice in `profile.yaml`.
2. An interactive terminal menu prompts:
   ```text
   [A]pprove variant (1-3) | [E]dit | [R]egenerate | [S]kip / Quit:
   ```
3. Type `A` and select `1` to approve Variant 1.
4. An approval record cryptographically bound to `text_sha256` is saved in your local database.

---

### Step 5: Publish Live to LinkedIn
Once you have reviewed and approved a draft, broadcast it to your live LinkedIn feed:
```bash
agent run --repo Naman-Dua/multimodal-attendance-engagement-agent --no-dry-run
```
The agent checks for your exact approval hash, calls LinkedIn's official Posts API, and returns your live post URL:
```text
✓ Post published successfully!
URL: https://www.linkedin.com/feed/update/urn:li:share:123456789
```

---

## Customizing Your Writing Voice

Edit `profile.yaml` to customize how the agent writes:
- **`tone`**: Builder-to-builder, direct, plain language.
- **`banned_phrases`**: Corporate buzzwords to automatically block ("excited to announce", "game-changer", "revolutionary").
- **`cta_styles`**: Soft calls-to-action (e.g. asking for technical feedback or linking repo).
- **`examples`**: Add your past top-performing LinkedIn posts as few-shot examples.

---

## Verification & Quality Gates

Run the automated test suite, style linter, and static type checker:
```bash
# Run unit & hardening test suite (51 tests)
pytest -q

# Format & lint check
ruff check .

# Strict type check
mypy src
```
