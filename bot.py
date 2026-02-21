"""
Unzip & File Manager Bot
Developer : @Venuboyy
"""
import os
import asyncio
import logging
from aiohttp import web
from pyrogram import Client
from config import Config
from utils import temp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("UnzipBot")

os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)


# ─── Web server (health check on port 8080) ──────────────────────────────────
async def health(request):
    return web.Response(text="✅ Unzip Bot is running!")


async def start_web():
    app  = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", Config.PORT)
    await site.start()
    log.info(f"Web server started on port {Config.PORT}")


# ─── Bot clients ─────────────────────────────────────────────────────────────
def build_bot() -> Client:
    return Client(
        name="UnzipBot",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        workers=Config.MAX_WORKERS,
        plugins={"root": "plugins"},
        sleep_threshold=60,
    )


def build_user_client() -> Client | None:
    if not Config.SESSION_STRING:
        log.warning("SESSION_STRING not set — files >2 GB will use bot client (may fail).")
        return None
    return Client(
        name="UserSession",
        session_string=Config.SESSION_STRING,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        workers=10,
    )


# ─── Main ────────────────────────────────────────────────────────────────────
async def main():
    # Start web health server
    await start_web()

    # Start user client (for 4 GB uploads)
    user_client = build_user_client()
    if user_client:
        await user_client.start()
        temp.U_CLIENT = user_client
        me = await user_client.get_me()
        log.info(f"User client started as: {me.first_name} (@{me.username})")

    # Start bot
    bot = build_bot()
    await bot.start()
    temp.ME = await bot.get_me()
    log.info(f"Bot started: @{temp.ME.username}")

    # Log channel notice
    if Config.LOG_CHANNEL:
        try:
            await bot.send_message(
                Config.LOG_CHANNEL,
                f"✅ **Bot Started!**\n\n"
                f"Name: [{temp.ME.first_name}](https://t.me/{temp.ME.username})\n"
                f"Session: {'✅ User client active (4 GB support)' if user_client else '❌ Bot only (2 GB limit)'}"
            )
        except Exception as e:
            log.warning(f"Could not send startup message to log channel: {e}")

    log.info("Bot is running. Press Ctrl+C to stop.")
    await asyncio.Event().wait()   # Keep alive


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Stopped.")
