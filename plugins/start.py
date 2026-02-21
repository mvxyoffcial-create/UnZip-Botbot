import asyncio
import aiohttp
import logging
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from config import Config
from database import db
from script import script
from utils import check_force_sub, get_welcome_image, temp

log = logging.getLogger(__name__)

FORCE_CHANNELS = Config.FORCE_SUB_CHANNELS


def _start_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔰 Help",       callback_data="help"),
            InlineKeyboardButton("ℹ️ About",      callback_data="about"),
        ],
        [
            InlineKeyboardButton("⚙️ Settings",   callback_data="open_settings"),
            InlineKeyboardButton("💎 Premium",    callback_data="premium_info"),
        ],
        [
            InlineKeyboardButton("📢 Updates",    url="https://t.me/zerodev2"),
            InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/Venuboyy"),
        ],
        [
            InlineKeyboardButton(
                "➕ Add Me To Group",
                url=f"https://t.me/{bot_username}?startgroup=true"
            )
        ],
    ])


def _force_sub_keyboard(channels: list) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(f"Join @{ch}", url=f"https://t.me/{ch}")] for ch in channels]
    rows.append([InlineKeyboardButton("✅ I've Joined", callback_data="check_sub")])
    return InlineKeyboardMarkup(rows)


async def _send_welcome(client: Client, chat_id: int, user):
    image = await get_welcome_image()
    bot_info = await client.get_me()
    name = user.first_name if user else "there"
    kb   = _start_keyboard(bot_info.username)

    await client.send_photo(
        chat_id=chat_id,
        photo=image or Config.FORCE_IMAGE,
        caption=script.START_TXT.format(name),
        reply_markup=kb,
    )


@Client.on_message(filters.command("start") & filters.private)
async def start_private(client: Client, message: Message):
    user = message.from_user
    uid  = user.id

    # Register user
    await db.add_user(uid)

    # Check ban
    if await db.is_banned(uid):
        return await message.reply_text("🚫 You are banned from using this bot.")

    # Auto-premium for Telegram Premium users (owner always premium)
    if uid == Config.OWNER_ID or (hasattr(user, "is_premium") and user.is_premium):
        if not await db.is_premium(uid):
            import datetime
            expiry = datetime.datetime.utcnow() + datetime.timedelta(days=36500)  # 100 years
            await db.update_user({"id": uid, "expiry_time": expiry})

    # Force-subscribe check
    missing = await check_force_sub(client, uid, FORCE_CHANNELS)
    if missing:
        return await message.reply_photo(
            photo=Config.FORCE_IMAGE,
            caption=script.FORCE_SUB_TXT.format(user.first_name),
            reply_markup=_force_sub_keyboard(missing),
        )

    # Sticker → 2s → delete → welcome image
    try:
        stk = await message.reply_sticker(Config.START_STICKER)
        await asyncio.sleep(2)
        await stk.delete()
    except Exception:
        pass

    await _send_welcome(client, message.chat.id, user)


@Client.on_message(filters.command("start") & filters.group)
async def start_group(client: Client, message: Message):
    await db.add_chat(message.chat.id)
    bot_info = await client.get_me()
    await message.reply_text(
        script.GSTART_TXT.format(message.from_user.first_name if message.from_user else "there"),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📩 Start in PM", url=f"https://t.me/{bot_info.username}?start=start")
        ]])
    )


# ──────────────────────────────────────────────────────────────────────────────
# Force-sub callback
# ──────────────────────────────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^check_sub$"))
async def check_sub_cb(client: Client, query: CallbackQuery):
    uid  = query.from_user.id
    user = query.from_user
    missing = await check_force_sub(client, uid, FORCE_CHANNELS)
    if missing:
        await query.answer("❌ You haven't joined all channels yet!", show_alert=True)
        return
    await query.message.delete()
    await _send_welcome(client, query.message.chat.id, user)


# ──────────────────────────────────────────────────────────────────────────────
# Help / About callbacks
# ──────────────────────────────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^help$"))
async def help_cb(client: Client, query: CallbackQuery):
    await query.message.edit_caption(
        caption=script.HELP_TXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_start")]
        ])
    )


@Client.on_callback_query(filters.regex("^about$"))
async def about_cb(client: Client, query: CallbackQuery):
    me = await client.get_me()
    await query.message.edit_caption(
        caption=script.ABOUT_TXT.format(me.first_name, me.username),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_start")]
        ])
    )


@Client.on_callback_query(filters.regex("^back_start$"))
async def back_start_cb(client: Client, query: CallbackQuery):
    bot_info = await client.get_me()
    name = query.from_user.first_name
    await query.message.edit_caption(
        caption=script.START_TXT.format(name),
        reply_markup=_start_keyboard(bot_info.username),
    )


@Client.on_callback_query(filters.regex("^close_data$"))
async def close_cb(client: Client, query: CallbackQuery):
    await query.message.delete()


# ──────────────────────────────────────────────────────────────────────────────
# /help command
# ──────────────────────────────────────────────────────────────────────────────
@Client.on_message(filters.command("help"))
async def help_cmd(client: Client, message: Message):
    await message.reply_text(
        script.HELP_TXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Updates", url="https://t.me/zerodev2")]
        ])
    )
