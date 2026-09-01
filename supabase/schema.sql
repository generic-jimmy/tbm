-- ═══════════════════════════════════════════════════════════════════════════
--  TBM Pro — Supabase schema
--  Run once in the SQL Editor before first deploy.
--  The app also auto-creates these on startup via CREATE TABLE IF NOT EXISTS.
-- ═══════════════════════════════════════════════════════════════════════════

-- ── bots ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bots (
    id               BIGSERIAL PRIMARY KEY,
    token_hash       TEXT UNIQUE NOT NULL,
    token_encrypted  TEXT NOT NULL,       -- Fernet-encrypted with SECRET_KEY
    username         TEXT,
    name             TEXT,
    bot_id           BIGINT,
    storage_chat_id  BIGINT,              -- Telegram group for file forwarding
    is_active        BOOLEAN DEFAULT TRUE,
    last_poll_id     BIGINT DEFAULT 0,
    telethon_session TEXT,                -- StringSession — persisted between restarts
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ── chats ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chats (
    id          BIGSERIAL PRIMARY KEY,
    chat_id     BIGINT NOT NULL,
    bot_hash    TEXT NOT NULL,
    type        TEXT,
    title       TEXT,
    username    TEXT,
    first_seen  TIMESTAMPTZ DEFAULT NOW(),
    last_active TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(chat_id, bot_hash)
);

-- ── users ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    bot_hash   TEXT NOT NULL,
    first_name TEXT,
    last_name  TEXT,
    username   TEXT,
    is_bot     BOOLEAN DEFAULT FALSE,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, bot_hash)
);

-- ── messages ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id                  BIGSERIAL PRIMARY KEY,
    msg_id              BIGINT,
    bot_hash            TEXT NOT NULL,
    update_id           BIGINT,                     -- NULL for MTProto messages
    kind                TEXT NOT NULL,
    sender_id           BIGINT,
    sender_name         TEXT,
    chat_id             BIGINT,
    chat_title          TEXT,
    content             TEXT,
    caption             TEXT,
    file_id             TEXT,
    file_name           TEXT,
    file_size           BIGINT,
    mime_type           TEXT,
    tg_storage_msg_id   BIGINT,                     -- msg ID in storage group
    tg_storage_file_id  TEXT,                       -- permanent file_id after forwarding
    is_forwarded        BOOLEAN DEFAULT FALSE,
    fwd_from            TEXT,
    reply_to_id         BIGINT,
    is_edited           BOOLEAN DEFAULT FALSE,
    is_deleted          BOOLEAN DEFAULT FALSE,
    width               INTEGER,
    height              INTEGER,
    duration            INTEGER,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    raw_json            JSONB,
    source              TEXT DEFAULT 'bot_api',     -- 'bot_api' | 'telethon'
    ts                  TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Bot API dedup: unique on (update_id, bot_hash) where update_id not null
CREATE UNIQUE INDEX IF NOT EXISTS idx_msg_botapi_dedup
    ON messages(update_id, bot_hash)
    WHERE update_id IS NOT NULL;

-- MTProto dedup: unique on (msg_id, chat_id, bot_hash) for telethon rows
CREATE UNIQUE INDEX IF NOT EXISTS idx_msg_telethon_dedup
    ON messages(msg_id, chat_id, bot_hash)
    WHERE source = 'telethon';

-- General query indexes
CREATE INDEX IF NOT EXISTS idx_msg_bot_hash  ON messages(bot_hash);
CREATE INDEX IF NOT EXISTS idx_msg_chat_id   ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_msg_kind      ON messages(kind);
CREATE INDEX IF NOT EXISTS idx_msg_ts        ON messages(ts DESC);
CREATE INDEX IF NOT EXISTS idx_msg_file_id   ON messages(file_id) WHERE file_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_msg_sender_id ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_msg_source    ON messages(source);
CREATE INDEX IF NOT EXISTS idx_chat_bot      ON chats(bot_hash);
CREATE INDEX IF NOT EXISTS idx_user_bot      ON users(bot_hash);

-- ── import_jobs ───────────────────────────────────────────────────────────
-- Tracks MTProto history import progress
CREATE TABLE IF NOT EXISTS import_jobs (
    id           TEXT PRIMARY KEY,                  -- short hex job ID
    bot_hash     TEXT NOT NULL,
    chat_id      BIGINT,                            -- NULL = all chats
    status       TEXT DEFAULT 'pending',            -- pending|running|done|error
    total        INTEGER DEFAULT 0,
    imported     INTEGER DEFAULT 0,
    skipped      INTEGER DEFAULT 0,
    current_chat TEXT,
    error        TEXT,
    started_at   TIMESTAMPTZ DEFAULT NOW(),
    finished_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_jobs_bot ON import_jobs(bot_hash);

-- ── import_checkpoints ────────────────────────────────────────────────────
-- Resumable full-history imports (earliest_id) + incremental re-sync (latest_id)
CREATE TABLE IF NOT EXISTS import_checkpoints (
    bot_hash    TEXT NOT NULL,
    chat_id     BIGINT NOT NULL,
    earliest_id BIGINT,
    latest_id   BIGINT,
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (bot_hash, chat_id)
);

-- ── message_templates ─────────────────────────────────────────────────────
-- Saved replies for Compose
CREATE TABLE IF NOT EXISTS message_templates (
    id           BIGSERIAL PRIMARY KEY,
    name         TEXT NOT NULL,
    text         TEXT NOT NULL,
    reply_markup JSONB,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
