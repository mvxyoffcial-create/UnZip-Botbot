# 📦 Unzip & File Manager Bot

**Developer:** @Venuboyy  
**Library:** Pyrogram | **Language:** Python 3 | **DB:** MongoDB

---

## ✨ Features

- Extract ZIP, RAR, 7Z, TAR, TAR.GZ, TAR.BZ2 archives
- **Auto-filter** — select which extracted files to upload via inline buttons
- **4 GB uploads** via user Session String
- Force-subscribe to channels before use
- Premium system with Telegram Stars payment
- Custom thumbnails, spoiler effect, rename before upload
- Direct URL downloads with progress bar
- Settings menu — per-user toggles
- Real broadcast to users & groups with cancel button
- Port 8080 health check (Heroku/Railway/Render compatible)

---

## 🚀 Deployment

### Local / VPS

```bash
git clone <repo>
cd unzip_bot
cp .env.example .env
# Edit .env with your values
pip install -r requirements.txt
# Install system packages:
apt-get install -y p7zip-full unrar-free ffmpeg
python3 bot.py
```

### Docker

```bash
docker build -t unzipbot .
docker run --env-file .env unzipbot
```

### Heroku / Railway / Render

Set environment variables from `.env.example` in the dashboard, then deploy.

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Your bot token from @BotFather |
| `API_ID` | ✅ | From my.telegram.org |
| `API_HASH` | ✅ | From my.telegram.org |
| `MONGO_URI` | ✅ | MongoDB connection string |
| `SESSION_STRING` | ✅ | User session for 4 GB uploads |
| `OWNER_ID` | ✅ | Your Telegram user ID |
| `ADMINS` | ✅ | Space-separated admin IDs |
| `LOG_CHANNEL` | ❌ | Channel ID for logs |
| `PREMIUM_LOGS` | ❌ | Channel ID for premium logs |
| `PORT` | ❌ | Web server port (default: 8080) |

---

## 🧾 Generate Session String

```bash
python3 generate_session.py
```

---

## 📋 Commands

| Command | Access | Description |
|---|---|---|
| `/start` | All | Welcome & force-subscribe |
| `/help` | All | How to use |
| `/settings` | All | Per-user settings |
| `/info` | All | User info |
| `/myplan` | All | Check premium status |
| `/plan` | All | View premium plans |
| `/setthumb` | All | Set custom thumbnail |
| `/stats` | Admin | Bot statistics |
| `/broadcast` | Admin | Broadcast to all users |
| `/grp_broadcast` | Admin | Broadcast to all groups |
| `/banned` | Admin | List banned users |
| `/ban` | Admin | Ban a user |
| `/unban` | Admin | Unban a user |
| `/add_premium` | Admin | Add premium manually |
| `/remove_premium` | Admin | Remove premium |
| `/premium_users` | Admin | List premium users |
| `/get_premium` | Admin | Check user premium |
| `/clear_junk` | Admin | Clean blocked/deleted users |
