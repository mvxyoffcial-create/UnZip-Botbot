import os

class Config:
    # ─── Bot Credentials ────────────────────────────────────────────────────────
    BOT_TOKEN        = os.environ.get("BOT_TOKEN", "")
    API_ID           = int(os.environ.get("API_ID", 0))
    API_HASH         = os.environ.get("API_HASH", "")

    # Session string — used for 4 GB uploads via Telegram's user-account limits
    SESSION_STRING   = os.environ.get("SESSION_STRING", "")

    # ─── Database ────────────────────────────────────────────────────────────────
    MONGO_URI        = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    DATABASE_NAME    = os.environ.get("DATABASE_NAME", "unzipbot")

    # ─── Owner / Admins ─────────────────────────────────────────────────────────
    OWNER_ID         = int(os.environ.get("OWNER_ID", 6332768936))   # @Venuboyy
    ADMINS           = list(map(int, os.environ.get("ADMINS", str(OWNER_ID)).split()))

    # ─── Force-subscribe channels ────────────────────────────────────────────────
    FORCE_SUB_CHANNELS = ["zerodev2", "mvxyoffcail"]          # without @
    FORCE_IMAGE        = "https://i.ibb.co/pr2H8cwT/img-8312532076.jpg"
    # Add separate welcome image (you can use same or different image)
    WELCOME_IMAGE      = "https://i.ibb.co/pr2H8cwT/img-8312532076.jpg"

    # ─── Logs ────────────────────────────────────────────────────────────────────
    LOG_CHANNEL      = int(os.environ.get("LOG_CHANNEL", 0))
    PREMIUM_LOGS     = int(os.environ.get("PREMIUM_LOGS", 0))

    # ─── Limits ──────────────────────────────────────────────────────────────────
    FREE_LIMIT       = 2 * 1024 * 1024 * 1024    # 2 GB
    PREMIUM_LIMIT    = 4 * 1024 * 1024 * 1024    # 4 GB

    # ─── Download dir ────────────────────────────────────────────────────────────
    DOWNLOAD_DIR     = os.environ.get("DOWNLOAD_DIR", "/tmp/unzipbot")

    # ─── Workers ─────────────────────────────────────────────────────────────────
    MAX_WORKERS      = 500

    # ─── Sticker ─────────────────────────────────────────────────────────────────
    START_STICKER    = "CAACAgIAAxkBAAEQZtFpgEdROhGouBVFD3e0K-YjmVHwsgACtCMAAphLKUjeub7NKlvk2TgE"

    # ─── Star premium plans { stars: "duration string" } ─────────────────────────
    STAR_PREMIUM_PLANS = {
        50:  "1 month",
        100: "3 months",
        200: "1 year",
    }

    # ─── Web server ──────────────────────────────────────────────────────────────
    PORT             = int(os.environ.get("PORT", 8080))
