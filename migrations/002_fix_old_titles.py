"""
Migration 002: Fix old document titles.

Old documents may have:
- title = mode key ('transcription', 'structure', 'ideas') — wrong, should be text
- title = None with empty content — shows '—' in sidebar

This script regenerates titles for broken documents using _generate_title().
Also reports documents with empty content so they can be reviewed.

Usage (on server):
    cd ~/voice_bot/voice_assistant_bot
    source venv/bin/activate
    python migrations/002_fix_old_titles.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from database import DB_PATH, _generate_title, _strip_html

MODE_KEYS = {'transcription', 'structure', 'ideas'}


def run_migration():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Find documents with mode-key titles or null titles
    cursor.execute("""
        SELECT id, user_id, title, content, mode
        FROM documents
        WHERE is_deleted = 0
          AND (title IS NULL OR title IN ('transcription', 'structure', 'ideas'))
        ORDER BY id
    """)
    rows = cursor.fetchall()

    if not rows:
        print("✅ No documents need title migration.")
        conn.close()
        return

    print(f"Found {len(rows)} documents with broken/missing titles:\n")

    updated = 0
    empty_content = []

    for doc_id, user_id, old_title, content, mode in rows:
        if not content or not content.strip() or content.strip() == '<p></p>':
            empty_content.append((doc_id, old_title, mode))
            print(f"  ⚠️  Doc #{doc_id} (mode={mode}): EMPTY CONTENT — skipped")
            continue

        new_title = _generate_title(content, mode)
        cursor.execute(
            "UPDATE documents SET title = ? WHERE id = ?",
            (new_title, doc_id)
        )
        updated += 1
        print(f"  ✅ Doc #{doc_id} (mode={mode}): '{old_title}' → '{new_title}'")

    conn.commit()
    conn.close()

    print(f"\n✅ Updated {updated} document titles.")

    if empty_content:
        print(f"\n⚠️  {len(empty_content)} documents have empty content (nothing to extract title from):")
        for doc_id, old_title, mode in empty_content:
            print(f"  Doc #{doc_id} (mode={mode}, title='{old_title}')")
        print("\nThese are likely old documents saved before HTML conversion was added.")
        print("They will show '(пустой документ)' in the sidebar preview.")


if __name__ == "__main__":
    print(f"DB path: {DB_PATH}")
    print("Running migration 002: Fix old document titles\n")
    run_migration()
