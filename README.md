<div align="center">

# 🚀 LinkedIn Post Agent

### *Turn your Git commits into high-signal engineering stories — with zero cringe, zero hallucinations, and mandatory human approval.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![Tests: 51 Passed](https://img.shields.io/badge/Tests-51%20Passed-success.svg?logo=pytest&logoColor=white)](tests)
[![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-black.svg)](https://github.com/astral-sh/ruff)
[![Type Check: Mypy Strict](https://img.shields.io/badge/Type%20Check-Mypy%20Strict-blue.svg)](https://mypy-lang.org)
[![Security: Audited](https://img.shields.io/badge/Security%20Audit-Verified-brightgreen.svg)](#security--privacy-guarantees)

[Features](#-key-features) • [How It Works](#-how-it-works) • [Quickstart](#-quickstart-in-30-seconds) • [Credentials Guide](#-step-by-step-credentials-guide) • [CLI Commands](#-cli-command-cheatsheet) • [License](#-license)

---

</div>

## 💡 Why This Exists

Most automated LinkedIn tools generate generic AI fluff: *"I am thrilled to announce my game-changing, revolutionary project! Agree? #hustle"*.

**Engineers hate reading it. Engineers hate writing it.**

**LinkedIn Post Agent** is different. It is a **local-first Python CLI** that reads your actual GitHub commits, repository READMEs, and technical project notes to generate authentic, builder-to-builder technical stories.

Most importantly: **it cannot publish without you.** Every single post is gated behind a cryptographic content-hash approval check. If you don't approve the exact SHA-256 hash, not a single byte is sent to LinkedIn.

---

## ⚡ Interactive Terminal Experience

```text
$ agent run --repo Naman-Dua/multimodal-attendance-engagement-agent --dry-run

=== Project Context: Naman-Dua/multimodal-attendance-engagement-agent ===
[✓] Fetched 5 recent commits (latest: 2e870a4)
[✓] Ingested README & sanitized sensitive credentials
[✓] Generated 3 grounded draft variants via Gemini

--- [Variant 1: Problem → Solution] ---
Taking attendance manually in a lecture wastes 10 minutes every session, but streaming video
to cloud vision APIs introduces serious privacy and bandwidth issues.

I built a multimodal classroom intelligence agent that runs locally on video and audio streams
to track attendance and surface real-time engagement insights.

Stack: Python, OpenCV, FastAPI, SQLAlchemy, Streamlit, Groq (Llama 3).

Here is how the pipeline works:
- Video frames process locally using OpenCV with spatial centroid tracking.
- Attendance is guarded by a sustained presence threshold (3.0 seconds minimum) so passersby
  outside the door are never falsely logged.
- Visual attention is fused with audio signals (speech-to-silence ratio and room noise levels).

Code: https://github.com/Naman-Dua/multimodal-attendance-engagement-agent
#python #computervision #aiagents #buildinpublic

Cited Claims:
  ✓ OpenCV spatial centroid tracking with distance matching  (Source: backend/pipeline.py)
  ✓ 3.0-second sustained attendance presence threshold       (Source: backend/pipeline.py)
  ✓ Dual-engine face detector with HSV fallback              (Source: Commit 1bc719a)

[A]pprove variant (1-3) | [E]dit | [R]egenerate | [S]kip / Quit: A 1
✓ Draft #1 Approved! (Hash: 4cb64e5468...)
[DRY RUN] Network publication skipped. Run with --no-dry-run to broadcast.
```

---

## 🌟 Key Features

| Feature | What It Does | Why It Matters |
| :--- | :--- | :--- |
| 🛡️ **Cryptographic Approval Gate** | Binds approvals to the exact post hash (`text_sha256`). | Zero accidental posts. Any text edit immediately invalidates prior sign-off. |
| 🔍 **Zero-Hallucination Grounding** | Verifies every metric & claim against git history. | Blocks fabricated benchmarks, fake user statistics, and false corporate claims. |
| 🧹 **In-Transit Secret Redaction** | Strips API keys, passwords, bearer tokens & emails. | Prevents repository secrets from ever reaching third-party LLMs. |
| 📱 **Omni-Channel Approval** | Review in terminal CLI or via Telegram Bot. | Tap inline buttons (`✓ Approve`, `✏ Edit`, `🔄 Regen`, `✕ Skip`) from your phone. |
| 🎯 **Smart Repo Suggestion Engine** | Scores repositories by activity & unposted status. | Eliminates writer's block by telling you what project to talk about next. |
| ⚡ **Safe Dry-Run by Default** | `DRY_RUN=true` is hardcoded as default. | Impossible to accidentally post live without explicit `--no-dry-run`. |

---

## 🏗️ Architecture

```
                    ┌──────────────┐      ┌──────────────┐
  GitHub Repos ────▶│ Ingestor     │─────▶│ Context      │
  Local Notes  ────▶│ (github.py)  │      │ Builder      │
                    └──────────────┘      └──────┬───────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │ LLM Drafter  │
                                          │ (Gemini/Son) │
                                          └──────┬───────┘
                                                 │ drafts[]
                                                 ▼
┌─────────────────┐                       ┌──────────────┐
│  State (SQLite) │◀──────────────────────│ Claims Check │ (Verifies git facts)
└────────┬────────┘                       └──────┬───────┘
         │                                       │
         │ approved(text_sha256)                 ▼
         │                                ┌──────────────┐  [✏ Edit / 🔄 Regen]
         │                                │ Approval Gate│◀──────────────────┐
         │                                │ CLI/Telegram │───────────────────┘
         │                                └──────┬───────┘
         ▼                                       │ verified hash
  ┌─────────────┐                                ▼
  │ Audit Log   │                         ┌──────────────┐
  │ (audit.json)│                         │ Publisher    │──▶ LinkedIn Posts API
  └─────────────┘                         └──────────────┘
```

---

## 🚀 Quickstart in 30 Seconds

```bash
# 1. Clone repository
git clone https://github.com/Naman-Dua/linkedin-agent.git
cd linkedin-agent

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Create .env file from template
# Windows (PowerShell):
Copy-Item .env.example .env
# Linux / macOS:
cp .env.example .env

# 4. Check status & run safe dry-run
agent auth status
agent suggest
agent run --repo <your-username/repo-name> --dry-run
```

---

## 🔑 Step-by-Step Credentials Guide

Follow these quick steps to fill your `.env` file:

### 1. Google Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Click **"Create API Key"** and copy the string (starts with `AIzaSy...`).
3. Set in `.env`:
   ```ini
   LLM_PROVIDER=gemini
   LLM_API_KEY=AIzaSy...your_gemini_key
   LLM_MODEL=gemini-3.5-flash
   ```
   *(Note: `gemini-3.5-flash` is fast, high-capacity, and cost-effective).*

---

### 2. GitHub Personal Access Token
Prevents API rate limits when pulling commits, tags, and READMEs:
1. Go to [GitHub Developer Settings $\rightarrow$ Fine-grained tokens](https://github.com/settings/tokens?type=beta).
2. Click **"Generate new token"**.
3. Under **Repository permissions**, grant:
   - **Contents:** `Read-only`
   - **Metadata:** `Read-only`
4. Set in `.env`:
   ```ini
   GITHUB_TOKEN=github_pat_...your_token
   ```

---

### 3. LinkedIn Developer App & OAuth Setup

#### A. Create a Company Page (Takes 30 seconds)
LinkedIn requires an associated company page where you are an admin. Do **not** use your university or workplace page unless you are a Super Admin.
1. Visit [LinkedIn Company Setup](https://www.linkedin.com/company/setup/new/).
2. Select **Company**, name it after your personal brand (e.g. `Naman Projects`), and click **Create page**. You are now instantly a Super Admin.

#### B. Create the Developer App
1. Go to the [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps/new).
2. Enter your App Name and select the company page you created in Step A.
3. Check the terms and click **Create app**.

#### C. Request Products (Permissions)
1. Go to the **Products** tab in your app.
2. Request **Share on LinkedIn** (provides `w_member_social`).
3. Request **Sign In with LinkedIn using OpenID Connect** (provides `openid`, `profile`).
*(Both approve immediately).*

#### D. Configure Redirect URI
1. Go to the **Auth** tab $\rightarrow$ **OAuth 2.0 settings**.
2. Under **Authorized redirect URLs**, add:
   ```text
   http://localhost:8080/callback
   ```
3. Copy **Client ID** and **Client Secret** into `.env`:
   ```ini
   LINKEDIN_CLIENT_ID=your_client_id
   LINKEDIN_CLIENT_SECRET=your_client_secret
   LINKEDIN_REDIRECT_URI=http://localhost:8080/callback
   LINKEDIN_VERSION=202601
   ```
4. Authenticate once via your terminal:
   ```bash
   agent auth login
   ```
   *Your browser will open $\rightarrow$ click **Allow** $\rightarrow$ access token is securely saved to your local database.*

---

### 4. Telegram Approval Bot (Optional — Mobile Review)
Review and approve drafts from your phone via interactive buttons:
1. Open Telegram, search for `@BotFather`, and send `/newbot`.
2. Follow prompts to name your bot and copy the **HTTP API token**.
3. Search for `@userinfobot`, press **Start**, and copy your numeric **Id**.
4. Set in `.env`:
   ```ini
   TELEGRAM_BOT_TOKEN=7123456789:AAH...
   TELEGRAM_CHAT_ID=123456789
   ```
5. Message your bot once (`/start`) so it has permission to message you.

---

## 🛠️ CLI Command Cheatsheet

| Command | Description | Example |
| :--- | :--- | :--- |
| `agent auth status` | Check GitHub & LinkedIn token validity & expiration | `agent auth status` |
| `agent auth login` | Complete browser-based LinkedIn OAuth loop | `agent auth login` |
| `agent suggest` | Rank your repositories by activity and unposted history | `agent suggest --limit 5` |
| `agent context` | Preview ingested commits, README, and redacted notes | `agent context --repo owner/repo` |
| `agent draft` | Generate 3 grounded drafts without interactive prompt | `agent draft --repo owner/repo` |
| `agent run --dry-run` | **Interactive review & approval** (Safe mode) | `agent run --repo owner/repo --dry-run` |
| `agent run --no-dry-run` | **Live publication** (Requires prior matching approval) | `agent run --repo owner/repo --no-dry-run` |

---

## 🎨 Customizing Your Writing Voice

Edit [`profile.yaml`](profile.yaml) to tailor the drafter to your personal style:

```yaml
name: "Your Name"
role: "Full-Stack Engineer"
tone: "builder-to-builder, direct, plain language, technical"
audience: "developers, engineering leads, founders"

length:
  min_chars: 900
  max_chars: 1500

banned_phrases:
  - "excited to announce"
  - "game-changer"
  - "revolutionary"
  - "agree?"
  - "blazing fast"

cta_styles:
  - "Check out the repo here: {repo_url}"
  - "What approach would you have taken? Repo link: {repo_url}"
```

---

## 🔒 Security & Privacy Guarantees

- **Zero Secret Commits:** `.gitignore` excludes all `.env*` files, SQLite databases, and tokens.
- **In-Memory Redaction:** Regular expressions automatically mask API keys, passwords, and emails in READMEs and commits before sending context to LLMs.
- **Strict Allowlist:** The Telegram bot strictly verifies incoming chat IDs against `TELEGRAM_CHAT_ID`, preventing unauthorized approvals.
- **Full Audit Trail:** All approval, edit, skip, and publication events are permanently recorded to an append-only JSONL log (`audit.jsonl`).

---

## 🧪 Verification & Quality Gates

Run the test suite, style linter, and static type checker:

```bash
# Run unit & hardening test suite (51 passed)
pytest -q

# Format & style check
ruff check .

# Strict type check
mypy src
```

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

---

<div align="center">
  <b>Built with care by <a href="https://github.com/Naman-Dua">Naman Dua</a></b>
</div>
