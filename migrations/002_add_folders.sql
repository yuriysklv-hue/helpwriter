-- Migration 002: Add folders table and folder_id to documents
-- Run manually on existing databases if needed.
-- New installs: init_database() in database.py handles this automatically.

CREATE TABLE IF NOT EXISTS folders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    parent_id  INTEGER,
    name       TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)   REFERENCES users(id),
    FOREIGN KEY (parent_id) REFERENCES folders(id)
);

CREATE INDEX IF NOT EXISTS idx_folders_user_id ON folders(user_id);

-- Add folder_id to documents (NULL = "Новые" / inbox)
ALTER TABLE documents ADD COLUMN folder_id INTEGER REFERENCES folders(id);
