"""SQLite database implementation with parameterized queries and WAL mode."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from linkedin_agent.store.models import ApprovalRecord, DraftRecord, PostRecord


class Database:
    """Manages SQLite storage for drafts, approvals, and published posts."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            data_dir = Path.home() / ".local" / "share" / "linkedin_agent"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(data_dir / "agent.db")
        else:
            self.db_path = str(db_path)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Create and configure a new SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def init_db(self) -> None:
        """Initialize database tables."""
        with self.get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo TEXT NOT NULL,
                    variant_no INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    text_sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    parent_draft_id INTEGER REFERENCES drafts(id)
                );

                CREATE TABLE IF NOT EXISTS approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_id INTEGER NOT NULL REFERENCES drafts(id),
                    text_sha256 TEXT NOT NULL,
                    approved_at TEXT NOT NULL,
                    channel TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_id INTEGER NOT NULL REFERENCES drafts(id),
                    linkedin_urn TEXT NOT NULL,
                    url TEXT,
                    posted_at TEXT NOT NULL,
                    idempotency_key TEXT UNIQUE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tokens_meta (
                    provider TEXT PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_drafts_sha ON drafts(text_sha256);
                CREATE INDEX IF NOT EXISTS idx_approvals_sha ON approvals(text_sha256);
                CREATE INDEX IF NOT EXISTS idx_posts_idempotency ON posts(idempotency_key);
                """
            )

    def save_draft(
        self,
        repo: str,
        variant_no: int,
        text: str,
        text_sha256: str,
        status: str = "CREATED",
        parent_draft_id: int | None = None,
    ) -> int:
        """Insert a new draft record."""
        now = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO drafts (
                    repo, variant_no, text, text_sha256, status, created_at, parent_draft_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (repo, variant_no, text, text_sha256, status, now, parent_draft_id),
            )
            return int(cur.lastrowid or 0)

    def get_draft(self, draft_id: int) -> DraftRecord | None:
        """Retrieve draft by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT id, repo, variant_no, text, text_sha256, status, "
                "created_at, parent_draft_id FROM drafts WHERE id = ?",
                (draft_id,),
            ).fetchone()
            if not row:
                return None
            return DraftRecord(
                id=row["id"],
                repo=row["repo"],
                variant_no=row["variant_no"],
                text=row["text"],
                text_sha256=row["text_sha256"],
                status=row["status"],
                created_at=row["created_at"],
                parent_draft_id=row["parent_draft_id"],
            )

    def update_draft_status(self, draft_id: int, status: str) -> None:
        """Update draft status."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE drafts SET status = ? WHERE id = ?",
                (status, draft_id),
            )

    def record_approval(self, draft_id: int, text_sha256: str, channel: str = "cli") -> int:
        """Record explicit approval bound to exact SHA256 content hash."""
        now = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO approvals (draft_id, text_sha256, approved_at, channel)
                VALUES (?, ?, ?, ?)
                """,
                (draft_id, text_sha256, now, channel),
            )
            conn.execute("UPDATE drafts SET status = 'APPROVED' WHERE id = ?", (draft_id,))
            return int(cur.lastrowid or 0)

    def get_approval_by_hash(self, text_sha256: str) -> ApprovalRecord | None:
        """Find matching approval for exact content hash."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT id, draft_id, text_sha256, approved_at, channel FROM approvals "
                "WHERE text_sha256 = ? ORDER BY id DESC LIMIT 1",
                (text_sha256,),
            ).fetchone()
            if not row:
                return None
            return ApprovalRecord(
                id=row["id"],
                draft_id=row["draft_id"],
                text_sha256=row["text_sha256"],
                approved_at=row["approved_at"],
                channel=row["channel"],
            )

    def record_post(
        self,
        draft_id: int,
        linkedin_urn: str,
        url: str | None,
        idempotency_key: str,
    ) -> int:
        """Record a successful post publication."""
        now = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO posts (draft_id, linkedin_urn, url, posted_at, idempotency_key)
                VALUES (?, ?, ?, ?, ?)
                """,
                (draft_id, linkedin_urn, url, now, idempotency_key),
            )
            conn.execute("UPDATE drafts SET status = 'PUBLISHED' WHERE id = ?", (draft_id,))
            return int(cur.lastrowid or 0)

    def get_post_by_idempotency_key(self, idempotency_key: str) -> PostRecord | None:
        """Find existing post by idempotency key."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT id, draft_id, linkedin_urn, url, posted_at, idempotency_key FROM posts "
                "WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if not row:
                return None
            return PostRecord(
                id=row["id"],
                draft_id=row["draft_id"],
                linkedin_urn=row["linkedin_urn"],
                url=row["url"],
                posted_at=row["posted_at"],
                idempotency_key=row["idempotency_key"],
            )

    def has_repo_been_posted(self, repo: str) -> bool:
        """Check if repo has already been posted to LinkedIn."""
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM posts p
                JOIN drafts d ON p.draft_id = d.id
                WHERE d.repo = ? LIMIT 1
                """,
                (repo,),
            ).fetchone()
            return row is not None

    def save_token(self, provider: str, access_token: str, expires_at: str) -> None:
        """Upsert OAuth token metadata."""
        now = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tokens_meta (provider, access_token, expires_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(provider) DO UPDATE SET
                    access_token = excluded.access_token,
                    expires_at = excluded.expires_at,
                    updated_at = excluded.updated_at
                """,
                (provider, access_token, expires_at, now),
            )

    def get_token(self, provider: str) -> tuple[str, str] | None:
        """Retrieve token and expires_at for provider."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT access_token, expires_at FROM tokens_meta WHERE provider = ?",
                (provider,),
            ).fetchone()
            if not row:
                return None
            return row["access_token"], row["expires_at"]
