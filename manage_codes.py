"""
Utility script to manage access codes for Voice Assistant Bot

Usage:
    python manage_codes.py add <code1> <code2> ...
    python manage_codes.py list
    python manage_codes.py remove <code>
    python manage_codes.py stats
"""

import sys
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "bot_database.db")


def add_code(code: str):
    """Add a new access code."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO access_codes (code, created_at) VALUES (?, CURRENT_TIMESTAMP)",
            (code,)
        )
        conn.commit()
        print(f"✅ Code '{code}' added successfully")
    except sqlite3.IntegrityError:
        print(f"⚠️ Code '{code}' already exists")
    finally:
        conn.close()


def list_codes():
    """List all access codes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT code, telegram_user_id, assigned_at, created_at, is_active
        FROM access_codes
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("📋 No access codes found")
        return

    print("📋 Access Codes:\n")
    for row in rows:
        code, user_id, assigned_at, created_at, is_active = row

        status = "✅ Active" if is_active else "❌ Inactive"
        user_info = f"User ID: {user_id}" if user_id else "Not assigned"

        print(f"🔑 {code}")
        print(f"   {status}")
        print(f"   {user_info}")
        print(f"   Created: {created_at}")
        if assigned_at:
            print(f"   Assigned: {assigned_at}")
        print()


def remove_code(code: str):
    """Deactivate an access code."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("UPDATE access_codes SET is_active = 0 WHERE code = ?", (code,))
    conn.commit()
    changes = cursor.rowcount
    conn.close()

    if changes > 0:
        print(f"✅ Code '{code}' deactivated")
    else:
        print(f"⚠️ Code '{code}' not found")


def show_stats():
    """Show usage statistics."""
    from database import get_admin_stats

    stats = get_admin_stats()

    print("📊 Usage Statistics:\n")

    for stat in stats:
        print(f"🔑 Code: {stat['code']}")
        print(f"   👤 User ID: {stat['user_id'] if stat['user_id'] else 'Not activated'}")
        print(f"   📨 Total messages: {stat['total_messages']}")
        print(f"   🎤 Voice messages: {stat['voice_messages']}")
        print(f"   📝 Text messages: {stat['text_messages']}")

        if stat['total_audio_duration']:
            minutes = stat['total_audio_duration'] / 60
            print(f"   ⏱️ Total audio: {minutes:.1f} min")

        if stat['total_text_characters']:
            print(f"   📊 Total text: {stat['total_text_characters']:,} characters")

        if stat['first_usage']:
            print(f"   📅 First usage: {stat['first_usage']}")
        if stat['last_usage']:
            print(f"   📅 Last usage: {stat['last_usage']}")

        print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    if command == "add":
        if len(sys.argv) < 3:
            print("Usage: python manage_codes.py add <code1> <code2> ...")
            return

        for code in sys.argv[2:]:
            add_code(code)

    elif command == "list":
        list_codes()

    elif command == "remove":
        if len(sys.argv) < 3:
            print("Usage: python manage_codes.py remove <code>")
            return

        remove_code(sys.argv[2])

    elif command == "stats":
        show_stats()

    else:
        print(f"❌ Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
