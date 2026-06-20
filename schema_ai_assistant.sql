-- KI-Assistent Tabellen für Supabase
-- Einmalig in Supabase SQL-Editor ausführen

CREATE TABLE IF NOT EXISTS ai_sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS ai_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT,
    role TEXT,
    content TEXT,
    timestamp TEXT
);
CREATE INDEX IF NOT EXISTS ai_messages_session_idx ON ai_messages(session_id);

CREATE TABLE IF NOT EXISTS ai_memories (
    id BIGSERIAL PRIMARY KEY,
    category TEXT DEFAULT 'general',
    content TEXT,
    created_at TEXT
);
