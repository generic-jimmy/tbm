# Telegram Bot Manager Pro — Cloud Edition

> Multi-bot · Supabase · Docker · MTProto Full History · Real-time Web UI
> Deploy to Railway / Render / Fly.io with one command.

---

## ⚡ Quick Deploy

### Step 1 — Supabase

1. Create a free project at [supabase.com](https://supabase.com)
2. Open **SQL Editor**, paste and run `supabase/schema.sql`
3. Copy your **Database URL**:
   `Project Settings → Database → Connection string → URI`

### Step 2 — Telegram credentials

**Bot token** — from [@BotFather](https://t.me/BotFather)

**MTProto credentials** — required for full history import (free, one-time):
1. Go to [my.telegram.org](https://my.telegram.org)
2. Log in with your phone number
3. Click **API development tools**
4. Create an app (name/description can be anything)
5. Copy `App api_id` (integer) and `App api_hash` (string)

> No phone number or user account is used at runtime.
> Only `api_id` + `api_hash` + `bot_token` are needed — all with bot privileges.

### Step 3 — Environment variables

```env
DATABASE_URL=postgresql://postgres.[ref]:[password]@...supabase.com:6543/postgres
SECRET_KEY=<openssl rand -hex 32>
ADMIN_PASSWORD=your-password-here
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
```

### Step 4 — Deploy

**Railway** (recommended):
```bash
railway login && railway init && railway up
railway variables set DATABASE_URL=... SECRET_KEY=... ADMIN_PASSWORD=... \
  TELEGRAM_API_ID=... TELEGRAM_API_HASH=...
```

**Render**: Connect GitHub → Docker runtime → add env vars → deploy

**Fly.io**:
```bash
fly launch --no-deploy
fly secrets set DATABASE_URL=... SECRET_KEY=... ADMIN_PASSWORD=... \
  TELEGRAM_API_ID=... TELEGRAM_API_HASH=...
fly deploy
```

**Docker locally**:
```bash
cp .env.example .env  # fill in your values
docker compose up --build
# → open http://localhost:8000
```

---

## 🤖 Adding Bots

1. Web UI → **Bot Manager** → **Add Bot**
2. Paste your bot token from @BotFather
3. Optionally enter a **Storage Group** chat ID
   - Your bot must be **admin** in this group
   - All received files are forwarded there permanently (free unlimited storage)
4. Bot starts polling immediately

---

## 🔵 MTProto Full History Import

Unlike the Bot API (which only holds ~24h of pending updates),
MTProto can fetch the **complete message history** of any chat the bot is in,
going back to the first message ever sent.

**How to use:**
1. Ensure `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` are set in your env
2. Bot Manager → click any bot card → **Import History**
3. Optionally enter a specific Chat ID, or leave blank to import all known chats
4. Click **Start Import** — real-time progress appears via WebSocket

**In Live Monitor:**
- Use the **MTProto** source tab to filter imported messages
- Bot API and MTProto messages are shown together by default
- Each row has a `Bot API` or `MTProto` badge for clarity

**What MTProto can access (as a bot):**
- ✅ Full history of any group/channel the bot is currently a member of
- ✅ Messages going back to the very first one in that chat
- ✅ All types: text, media, documents, polls, forwards, replies
- ❌ DMs between other users
- ❌ Messages from before the bot joined the chat (Telegram server enforces this)

---

## 🏗 Architecture

```
Browser (React SPA)
    ↕  REST API + WebSocket
FastAPI (single Docker container)
    ├─ Bot Worker × N     (asyncio task per bot — live polling)
    │   ├─ Bot API drain  (pending queue on boot)
    │   ├─ Live polling   (getUpdates every ~0.8s)
    │   └─ File forward   (→ Telegram Storage Group)
    ├─ History Importer   (MTProto via Telethon, triggered on demand)
    │   ├─ StringSession  (persisted in Supabase — survives restarts)
    │   ├─ iter_messages  (full chat history, unlimited depth)
    │   └─ WS progress    (real-time job updates to browser)
    └─ asyncpg pool       (→ Supabase PostgreSQL)
```

## 🧑‍💻 Local Development

```bash
# Backend
pip install -r requirements.txt
cp .env.example .env   # fill in your values
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev   # Vite on :3000, proxies /api and /ws to :8000
```
