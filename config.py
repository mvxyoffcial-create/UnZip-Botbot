import os

class Config:
    # ─── Bot Credentials ────────────────────────────────────────────────────────
    BOT_TOKEN        = "8337890824:AAFj6iqXNSovFQOAWTRAtbblJIlPtcu2IYw"
    API_ID           = 20288994
    API_HASH         = "d702614912f1ad370a0d18786002adbf"

    # Session string — used for 4 GB uploads via Telegram's user-account limits
    SESSION_STRING   = "BQE1leIAQ91QBxeeXOVyv4pFbVCZlK-lwgQCTge8tptNm8H8K3s1LedpPDYDOKhyqkNztGmXMOuBIfwezqN02GRf6NPEEtLI_78tNqvV9Amb_0Iw3FA-cJwYX-AnRYWG_dqTvfNWoA8lIa2GTz3SSsZdu2l8eb4rfQHxCGSsbAy5leT7yJbOWDzCWFA2_iLnEgPoovkmTMuliKmyvAe6feHfaPGCd-pLCpRKSE26S1UzsG0Tw0M1JJZVGqfOrx9_CiREP1oytxPMUVBTAzQNlJn6L1EeYwZ38qQ9kKqw8M3mBysKo6UhzwGbX1eV84Le5DiZAUezBw7CZnWbj1ZVTvBWut2kZQAAAAHjUB8sAA"

    # ─── Database ────────────────────────────────────────────────────────────────
    MONGO_URI        = "mongodb+srv://Veggo:zero8907@cluster0.o8sxezg.mongodb.net/?appName=Cluster0"
    DATABASE_NAME    = "unzipbot"

    # ─── Owner / Admins ─────────────────────────────────────────────────────────
    OWNER_ID         = 8108646188   # @Venuboyy
    ADMINS           = 8108646188

    # ─── Force-subscribe channels ────────────────────────────────────────────────
    FORCE_SUB_CHANNELS = ["zerodev2", "mvxyoffcail"]          # without @
    FORCE_IMAGE        = "https://i.ibb.co/pr2H8cwT/img-8312532076.jpg"
    # Add separate welcome image (you can use same or different image)
    WELCOME_IMAGE      = "https://i.ibb.co/Q7bPswdL/img-8108646188.jpg"

    # ─── Logs ────────────────────────────────────────────────────────────────────
    LOG_CHANNEL      = int(os.environ.get("LOG_CHANNEL", 0))
    PREMIUM_LOGS     = int(os.environ.get("PREMIUM_LOGS", 0))

    # ─── Limits ──────────────────────────────────────────────────────────────────
    FREE_LIMIT       = 2 * 1024 * 1024 * 1024    # 2 GB
    PREMIUM_LIMIT    = 4 * 1024 * 1024 * 1024    # 4 GB

    # ─── Download dir ────────────────────────────────────────────────────────────
    DOWNLOAD_DIR     = "/tmp/unzipbot"

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
    PORT             = 8080
