"""
Database module for Voice Assistant Bot
Handles access codes, user authentication, and usage analytics
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), "bot_database.db")


def init_database():
    """Initialize database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # WAL mode — allows concurrent reads (FastAPI) while bot is writing
    cursor.execute("PRAGMA journal_mode=WAL")

    # Create users table (for web app authentication)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            photo_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)")

    # Create documents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            mode TEXT NOT NULL,
            source TEXT DEFAULT 'bot',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_docs_user_id ON documents(user_id)")

    # Create access_codes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS access_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            telegram_user_id INTEGER,
            assigned_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            preferred_style TEXT DEFAULT 'transcription'
        )
    """)

    # Check and add preferred_style column if not exists (for migration)
    cursor.execute("PRAGMA table_info(access_codes)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'preferred_style' not in columns:
        logger.info("🔄 Migrating database: adding preferred_style column")
        cursor.execute("ALTER TABLE access_codes ADD COLUMN preferred_style TEXT DEFAULT 'transcription'")
        conn.commit()
        logger.info("✅ Migration completed")

    # Backfill titles for documents where title is NULL or is a raw mode key
    mode_keys = ('transcription', 'structure', 'ideas')
    placeholders = ','.join('?' for _ in mode_keys)
    cursor.execute(
        f"SELECT id, content, mode FROM documents WHERE title IS NULL OR title IN ({placeholders})",
        mode_keys,
    )
    rows_to_fix = cursor.fetchall()
    if rows_to_fix:
        logger.info(f"🔄 Backfilling titles for {len(rows_to_fix)} documents...")
        for doc_id, content, mode in rows_to_fix:
            title = _generate_title(content or '', mode or 'transcription')
            cursor.execute("UPDATE documents SET title=? WHERE id=?", (title, doc_id))
        conn.commit()
        logger.info("✅ Title backfill complete")

    # Create subscriptions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL,
            stars_payment_id TEXT NOT NULL,
            stars_amount INTEGER NOT NULL,
            period_days INTEGER NOT NULL,
            started_at TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_user ON subscriptions(telegram_user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_expires ON subscriptions(expires_at)")

    # Create usage_logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            access_code_id INTEGER,
            telegram_user_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message_type TEXT,
            audio_duration REAL,
            text_characters INTEGER,
            processing_time REAL,
            FOREIGN KEY (access_code_id) REFERENCES access_codes(id)
        )
    """)

    conn.commit()
    conn.close()
    logger.info("✅ Database initialized successfully")


def add_access_code(code: str) -> bool:
    """
    Add a new access code.

    Args:
        code: Access code string (e.g., "ritathebest")

    Returns:
        True if successful, False if code already exists
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO access_codes (code, created_at) VALUES (?, CURRENT_TIMESTAMP)",
            (code,)
        )

        conn.commit()
        conn.close()
        logger.info(f"✅ Access code '{code}' added successfully")
        return True
    except sqlite3.IntegrityError:
        logger.warning(f"⚠️ Access code '{code}' already exists")
        return False


def assign_code_to_user(code: str, telegram_user_id: int) -> tuple[bool, str]:
    """
    Assign an access code to a Telegram user.

    Args:
        code: Access code string
        telegram_user_id: Telegram user ID

    Returns:
        (success: bool, message: str)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if code exists and is active
    cursor.execute("SELECT id, telegram_user_id, is_active FROM access_codes WHERE code = ?", (code,))
    result = cursor.fetchone()

    if result is None:
        conn.close()
        return False, "❌ Код не найден. Проверьте правильность ввода."

    code_id, assigned_user_id, is_active = result

    if not is_active:
        conn.close()
        return False, "❌ Этот код деактивирован."

    # Check if code is already assigned to another user
    if assigned_user_id is not None and assigned_user_id != telegram_user_id:
        conn.close()
        return False, "❌ Этот код уже используется на другом устройстве."

    # If already assigned to this user, just confirm
    if assigned_user_id == telegram_user_id:
        conn.close()
        return True, "✅ Код уже активирован! Бот разблокирован."

    # Assign code to user
    cursor.execute(
        "UPDATE access_codes SET telegram_user_id = ?, assigned_at = CURRENT_TIMESTAMP WHERE id = ?",
        (telegram_user_id, code_id)
    )

    conn.commit()
    conn.close()
    logger.info(f"✅ Code '{code}' assigned to user {telegram_user_id}")
    return True, "✅ Код принят! Добро пожаловать!"


def check_user_access(telegram_user_id: int) -> Optional[str]:
    """
    Check if user has access (has assigned code).

    Args:
        telegram_user_id: Telegram user ID

    Returns:
        Access code if user has access, None otherwise
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT code FROM access_codes WHERE telegram_user_id = ? AND is_active = 1",
        (telegram_user_id,)
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]
    return None


def create_auto_access_code(telegram_user_id: int) -> int:
    """
    Automatically create access code for new user (open access).

    Args:
        telegram_user_id: Telegram user ID

    Returns:
        ID of created access code
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Generate unique code based on user_id
    auto_code = f"auto_{telegram_user_id}_{int(datetime.now().timestamp())}"

    # Create access code
    cursor.execute("""
        INSERT INTO access_codes
        (code, telegram_user_id, assigned_at, is_active, preferred_style)
        VALUES (?, ?, CURRENT_TIMESTAMP, 1, 'transcription')
    """, (auto_code, telegram_user_id))

    access_code_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"✅ Auto-created access code for user {telegram_user_id}: {auto_code}")
    return access_code_id


def log_usage(
    telegram_user_id: int,
    message_type: str,
    audio_duration: float = None,
    text_characters: int = None,
    processing_time: float = None
):
    """
    Log usage analytics. Creates access code automatically if user doesn't exist.

    Args:
        telegram_user_id: Telegram user ID
        message_type: Type of message ("voice" or "text")
        audio_duration: Audio duration in seconds (for voice messages)
        text_characters: Number of characters (raw text length)
        processing_time: Total processing time in seconds
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get access code ID (may be None for subscription-only users)
    cursor.execute(
        "SELECT id FROM access_codes WHERE telegram_user_id = ?",
        (telegram_user_id,)
    )
    result = cursor.fetchone()
    access_code_id = result[0] if result else None

    # Insert usage log
    cursor.execute("""
        INSERT INTO usage_logs
        (access_code_id, telegram_user_id, timestamp, message_type, audio_duration, text_characters, processing_time)
        VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
    """, (access_code_id, telegram_user_id, message_type, audio_duration, text_characters, processing_time))

    conn.commit()
    conn.close()
    logger.info(f"✅ Usage logged for user {telegram_user_id}: {message_type}")


def get_admin_stats() -> List[Dict]:
    """
    Get usage statistics per user from usage_logs.

    Returns:
        List of dicts with stats per telegram_user_id
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            ul.telegram_user_id,
            COUNT(ul.id) as total_messages,
            SUM(CASE WHEN ul.message_type = 'voice' THEN 1 ELSE 0 END) as voice_messages,
            SUM(CASE WHEN ul.message_type = 'text' THEN 1 ELSE 0 END) as text_messages,
            SUM(ul.audio_duration) as total_audio_duration,
            SUM(ul.text_characters) as total_text_characters,
            MIN(ul.timestamp) as first_usage,
            MAX(ul.timestamp) as last_usage
        FROM usage_logs ul
        GROUP BY ul.telegram_user_id
        ORDER BY last_usage DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    stats = []
    for row in rows:
        stats.append({
            "user_id": row[0],
            "total_messages": row[1] or 0,
            "voice_messages": row[2] or 0,
            "text_messages": row[3] or 0,
            "total_audio_duration": row[4] or 0.0,
            "total_text_characters": row[5] or 0,
            "first_usage": row[6],
            "last_usage": row[7],
        })

    return stats


def get_all_access_codes() -> List[str]:
    """Get list of all access codes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT code FROM access_codes ORDER BY created_at")
    rows = cursor.fetchall()
    conn.close()

    return [row[0] for row in rows]


def get_user_style(telegram_user_id: int) -> str:
    """
    Get user's preferred editing style.

    Args:
        telegram_user_id: Telegram user ID

    Returns:
        Style key (e.g., 'business_casual', 'formal', etc.)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT preferred_style FROM access_codes WHERE telegram_user_id = ?",
        (telegram_user_id,)
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]
    return 'transcription'  # Default mode


def set_user_style(telegram_user_id: int, style: str) -> bool:
    """
    Set user's preferred editing style.

    Args:
        telegram_user_id: Telegram user ID
        style: Style key to set

    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE access_codes SET preferred_style = ? WHERE telegram_user_id = ?",
            (style, telegram_user_id)
        )

        conn.commit()
        conn.close()
        logger.info(f"✅ User {telegram_user_id} style set to '{style}'")
        return True
    except Exception as e:
        logger.error(f"❌ Error setting user style: {e}")
        return False


def get_active_subscription(telegram_user_id: int) -> Optional[Dict]:
    """Return active subscription or None."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, stars_amount, period_days, started_at, expires_at
        FROM subscriptions
        WHERE telegram_user_id = ? AND is_active = 1 AND expires_at > CURRENT_TIMESTAMP
        ORDER BY expires_at DESC
        LIMIT 1
    """, (telegram_user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "id": result[0],
            "stars_amount": result[1],
            "period_days": result[2],
            "started_at": result[3],
            "expires_at": result[4],
        }
    return None


def create_subscription(telegram_user_id: int, payment_id: str, stars_amount: int, period_days: int) -> int:
    """Create subscription record. If active subscription exists, extends it. Returns record ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now()

    # Check for existing active subscription to extend from its expiry, not from now
    cursor.execute("""
        SELECT expires_at FROM subscriptions
        WHERE telegram_user_id = ? AND is_active = 1 AND expires_at > CURRENT_TIMESTAMP
        ORDER BY expires_at DESC LIMIT 1
    """, (telegram_user_id,))
    row = cursor.fetchone()
    base_date = datetime.fromisoformat(row[0]) if row else now
    expires_at = base_date + timedelta(days=period_days)

    cursor.execute("""
        INSERT INTO subscriptions
        (telegram_user_id, stars_payment_id, stars_amount, period_days, started_at, expires_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (telegram_user_id, payment_id, stars_amount, period_days, now.isoformat(), expires_at.isoformat()))
    sub_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"✅ Subscription created for user {telegram_user_id}, expires {expires_at.date()}")
    return sub_id


def get_expiring_subscriptions(days_before: int = 3) -> List[Dict]:
    """Return subscriptions expiring within N days (for reminders)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now()
    threshold = now + timedelta(days=days_before)
    cursor.execute("""
        SELECT telegram_user_id, expires_at
        FROM subscriptions
        WHERE is_active = 1
          AND expires_at > CURRENT_TIMESTAMP
          AND expires_at <= ?
    """, (threshold.isoformat(),))
    rows = cursor.fetchall()
    conn.close()
    return [{"user_id": r[0], "expires_at": r[1]} for r in rows]


def deactivate_expired_subscriptions() -> int:
    """Deactivate expired subscriptions. Returns number of affected rows."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE subscriptions SET is_active = 0
        WHERE expires_at <= CURRENT_TIMESTAMP AND is_active = 1
    """)
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected > 0:
        logger.info(f"✅ Deactivated {affected} expired subscriptions")
    return affected


def get_subscription_stats() -> Dict:
    """Return subscription stats for admin."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*), SUM(stars_amount)
        FROM subscriptions
        WHERE is_active = 1 AND expires_at > CURRENT_TIMESTAMP
    """)
    active_row = cursor.fetchone()
    cursor.execute("""
        SELECT SUM(stars_amount)
        FROM subscriptions
        WHERE started_at >= datetime('now', '-30 days')
    """)
    monthly_row = cursor.fetchone()
    conn.close()
    return {
        "active_subscriptions": active_row[0] or 0,
        "stars_last_30d": monthly_row[0] or 0,
    }


# =============================================================================
# USERS
# =============================================================================

def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities for plain text extraction."""
    import re, html
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text)


def _generate_title(content: str, mode: str) -> str:
    """Generate a short title from document content — first sentence of text."""
    # Strip HTML if content looks like HTML
    plain = _strip_html(content) if content.strip().startswith('<') else content

    # For structure/ideas modes try to extract the dedicated title line
    if mode == "structure":
        for line in plain.split('\n'):
            stripped = line.strip()
            if stripped.startswith('ТЕМА:'):
                title = stripped[5:].strip()
                if title:
                    return title[:80]
    elif mode == "ideas":
        for line in plain.split('\n'):
            stripped = line.strip()
            if stripped.startswith('Тема:'):
                title = stripped[5:].strip()
                if title:
                    return title[:80]

    # Default: first sentence from first non-empty, non-header line
    skip_prefixes = ('ТЕМА:', 'Тема:', 'ПЛАН:', 'ГЛАВНАЯ МЫСЛЬ:', 'ЗАМЕТКИ:')
    for line in plain.split('\n'):
        line = line.strip()
        if not line or any(line.startswith(p) for p in skip_prefixes):
            continue
        # Try to cut at first sentence boundary
        for sep in ('. ', '! ', '? '):
            idx = line.find(sep)
            if 0 < idx <= 80:
                return line[:idx + 1]
        return (line[:77] + '...') if len(line) > 80 else line
    return "Без названия"


def get_or_create_user(
    telegram_id: int,
    first_name: str = None,
    last_name: str = None,
    username: str = None,
    photo_url: str = None,
) -> int:
    """Get existing user or create new one. Returns user.id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    result = cursor.fetchone()
    if result:
        cursor.execute(
            "UPDATE users SET first_name=?, last_name=?, username=?, last_login_at=CURRENT_TIMESTAMP WHERE telegram_id=?",
            (first_name, last_name, username, telegram_id),
        )
        user_id = result[0]
    else:
        cursor.execute(
            "INSERT INTO users (telegram_id, first_name, last_name, username, photo_url) VALUES (?, ?, ?, ?, ?)",
            (telegram_id, first_name, last_name, username, photo_url),
        )
        user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_telegram_id(telegram_id: int) -> Optional[Dict]:
    """Return user dict by telegram_id, or None."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, telegram_id, first_name, last_name, username, photo_url, created_at, last_login_at FROM users WHERE telegram_id = ?",
        (telegram_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "telegram_id": row[1], "first_name": row[2],
            "last_name": row[3], "username": row[4], "photo_url": row[5],
            "created_at": row[6], "last_login_at": row[7],
        }
    return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Return user dict by internal id, or None."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, telegram_id, first_name, last_name, username, photo_url, created_at, last_login_at FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "telegram_id": row[1], "first_name": row[2],
            "last_name": row[3], "username": row[4], "photo_url": row[5],
            "created_at": row[6], "last_login_at": row[7],
        }
    return None


def update_last_login(user_id: int) -> None:
    """Update last_login_at for user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_login_at=CURRENT_TIMESTAMP WHERE id=?", (user_id,))
    conn.commit()
    conn.close()


# =============================================================================
# DOCUMENTS
# =============================================================================

def create_document(
    user_id: int,
    content: str,
    mode: str,
    title: str = None,
    source: str = "bot",
) -> int:
    """Create a document. Auto-generates title if not provided. Returns document.id."""
    if not title:
        title = _generate_title(content, mode)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (user_id, title, content, mode, source) VALUES (?, ?, ?, ?, ?)",
        (user_id, title, content, mode, source),
    )
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"✅ Document {doc_id} created for user {user_id} (mode={mode}, source={source})")
    return doc_id


def get_user_documents(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    mode: str = None,
) -> Dict:
    """Return paginated documents list for user. Excludes soft-deleted."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    where = "user_id = ? AND is_deleted = 0"
    params = [user_id]
    if mode:
        where += " AND mode = ?"
        params.append(mode)

    cursor.execute(f"SELECT COUNT(*) FROM documents WHERE {where}", params)
    total = cursor.fetchone()[0]

    cursor.execute(
        f"SELECT id, title, content, mode, source, created_at, updated_at FROM documents WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    )
    rows = cursor.fetchall()
    conn.close()

    items = []
    for row in rows:
        content_preview = row[2][:200] if row[2] else ""
        items.append({
            "id": row[0], "title": row[1], "preview": content_preview,
            "mode": row[3], "source": row[4], "created_at": row[5], "updated_at": row[6],
        })
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def get_document_by_id(doc_id: int, user_id: int) -> Optional[Dict]:
    """Return document by id, only if it belongs to user and is not deleted."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, title, content, mode, source, created_at, updated_at FROM documents WHERE id = ? AND user_id = ? AND is_deleted = 0",
        (doc_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "user_id": row[1], "title": row[2], "content": row[3],
            "mode": row[4], "source": row[5], "created_at": row[6], "updated_at": row[7],
        }
    return None


def update_document(doc_id: int, user_id: int, content: str = None, title: str = None) -> bool:
    """Update document content and/or title. Returns True if updated."""
    if content is None and title is None:
        return False
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if content is not None and title is not None:
        cursor.execute(
            "UPDATE documents SET content=?, title=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=? AND is_deleted=0",
            (content, title, doc_id, user_id),
        )
    elif content is not None:
        cursor.execute(
            "UPDATE documents SET content=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=? AND is_deleted=0",
            (content, doc_id, user_id),
        )
    else:
        cursor.execute(
            "UPDATE documents SET title=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=? AND is_deleted=0",
            (title, doc_id, user_id),
        )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def delete_document(doc_id: int, user_id: int) -> bool:
    """Soft-delete a document. Returns True if deleted."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE documents SET is_deleted=1, updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=? AND is_deleted=0",
        (doc_id, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_user_stats(user_id: int) -> Dict:
    """Return document usage stats for a user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*), SUM(CASE WHEN mode='transcription' THEN 1 ELSE 0 END), SUM(CASE WHEN mode='structure' THEN 1 ELSE 0 END), SUM(CASE WHEN mode='ideas' THEN 1 ELSE 0 END) FROM documents WHERE user_id=? AND is_deleted=0",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return {
        "total_documents": row[0] or 0,
        "transcription": row[1] or 0,
        "structure": row[2] or 0,
        "ideas": row[3] or 0,
    }


# Initialize database on import
init_database()
