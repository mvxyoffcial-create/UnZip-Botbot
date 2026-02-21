import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database import db
from utils import get_readable_time

log = logging.getLogger(__name__)
ADMINS = Config.ADMINS


@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats_cmd(client: Client, message: Message):
    total_users = await db.total_users_count()
    total_chats = await db.total_chat_count()
    await message.reply_text(
        f"📊 <b>Bot Statistics</b>\n\n"
        f"👤 <b>Total Users :</b> <code>{total_users}</code>\n"
        f"👥 <b>Total Groups :</b> <code>{total_chats}</code>"
    )


@Client.on_message(filters.command("banned") & filters.user(ADMINS))
async def banned_cmd(client: Client, message: Message):
    lines = []
    async for u in db.get_banned_users():
        try:
            user = await client.get_users(u["id"])
            lines.append(f"• {user.mention} (<code>{u['id']}</code>)")
        except Exception:
            lines.append(f"• <code>{u['id']}</code>")
    if lines:
        await message.reply_text("🚫 <b>Banned Users:</b>\n\n" + "\n".join(lines))
    else:
        await message.reply_text("✅ No banned users.")


@Client.on_message(filters.command("ban") & filters.user(ADMINS))
async def ban_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /ban user_id")
    uid = int(message.command[1])
    await db.ban_user(uid)
    await message.reply_text(f"🚫 User <code>{uid}</code> banned.")


@Client.on_message(filters.command("unban") & filters.user(ADMINS))
async def unban_cmd(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /unban user_id")
    uid = int(message.command[1])
    await db.unban_user(uid)
    await message.reply_text(f"✅ User <code>{uid}</code> unbanned.")


@Client.on_message(filters.command("restart") & filters.user(ADMINS))
async def restart_cmd(client: Client, message: Message):
    await message.reply_text("🔄 Restarting...")
    import os, sys
    os.execv(sys.executable, ["python"] + sys.argv)
