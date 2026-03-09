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
    Get comprehensive statistics for admin.

    Returns:
        List of dicts with stats per access code
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            ac.code,
            ac.telegram_user_id,
            ac.assigned_at,
            COUNT(ul.id) as total_messages,
            SUM(CASE WHEN ul.message_type = 'voice' THEN 1 ELSE 0 END) as voice_messages,
            SUM(CASE WHEN ul.message_type = 'text' THEN 1 ELSE 0 END) as text_messages,
            SUM(ul.audio_duration) as total_audio_duration,
            SUM(ul.text_characters) as total_text_characters,
            MIN(ul.timestamp) as first_usage,
            MAX(ul.timestamp) as last_usage
        FROM access_codes ac
        LEFT JOIN usage_logs ul ON ac.id = ul.access_code_id
        GROUP BY ac.code
        ORDER BY ac.created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    stats = []
    for row in rows:
        stats.append({
            "code": row[0],
            "user_id": row[1],
            "assigned_at": row[2],
            "total_messages": row[3] or 0,
            "voice_messages": row[4] or 0,
            "text_messages": row[5] or 0,
            "total_audio_duration": row[6] or 0.0,
            "total_text_characters": row[7] or 0,
            "first_usage": row[8],
            "last_usage": row[9]
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
    """Create subscription record, return its ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now()
    expires_at = now + timedelta(days=period_days)
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


# Initialize database on import
init_database()
