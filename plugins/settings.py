import pytz
import logging
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from database import db
from script import script

log = logging.getLogger(__name__)

TIMEZONES = ["Asia/Kolkata", "UTC", "US/Eastern", "US/Pacific", "Europe/London", "Asia/Dubai"]


def _on_off(val: bool) -> str:
    return "✅ ON" if val else "❌ OFF"


async def _settings_keyboard(uid: int) -> InlineKeyboardMarkup:
    u = await db.get_user(uid)
    if not u:
        u = {}
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💥 Spoiler Effect — {_on_off(u.get('spoiler', False))}",
                              callback_data="toggle_spoiler")],
        [InlineKeyboardButton(f"✏️ Rename Option — {_on_off(u.get('rename', True))}",
                              callback_data="toggle_rename")],
        [InlineKeyboardButton(f"📄 Upload as Document — {_on_off(u.get('as_document', False))}",
                              callback_data="toggle_doc")],
        [InlineKeyboardButton(f"📸 Receive Screenshots — {_on_off(u.get('screenshots', True))}",
                              callback_data="toggle_screenshots")],
        [InlineKeyboardButton(f"🤖 Bot Updates — {_on_off(u.get('bot_updates', True))}",
                              callback_data="toggle_updates")],
        [
            InlineKeyboardButton("🖼️ See Thumbnail",    callback_data="see_thumb"),
            InlineKeyboardButton("🗑️ Delete Thumbnail", callback_data="del_thumb"),
        ],
        [InlineKeyboardButton("🕒 Set Timezone", callback_data="set_timezone")],
        [InlineKeyboardButton("🔙 Close",        callback_data="close_data")],
    ])


@Client.on_message(filters.command("settings") & filters.private)
async def settings_cmd(client: Client, message: Message):
    uid = message.from_user.id
    await db.add_user(uid)
    kb = await _settings_keyboard(uid)
    await message.reply_text(script.SETTINGS_TXT, reply_markup=kb)


@Client.on_callback_query(filters.regex("^open_settings$"))
async def open_settings_cb(client: Client, query: CallbackQuery):
    uid = query.from_user.id
    kb  = await _settings_keyboard(uid)
    try:
        await query.message.edit_caption(caption=script.SETTINGS_TXT, reply_markup=kb)
    except Exception:
        await query.message.reply_text(script.SETTINGS_TXT, reply_markup=kb)
    await query.answer()


async def _toggle_and_refresh(client: Client, query: CallbackQuery, key: str):
    uid  = query.from_user.id
    nval = await db.toggle_setting(uid, key)
    kb   = await _settings_keyboard(uid)
    try:
        await query.message.edit_reply_markup(kb)
    except Exception:
        pass
    await query.answer(f"{'Enabled' if nval else 'Disabled'}")


@Client.on_callback_query(filters.regex("^toggle_spoiler$"))
async def toggle_spoiler(c, q): await _toggle_and_refresh(c, q, "spoiler")

@Client.on_callback_query(filters.regex("^toggle_rename$"))
async def toggle_rename(c, q): await _toggle_and_refresh(c, q, "rename")

@Client.on_callback_query(filters.regex("^toggle_doc$"))
async def toggle_doc(c, q): await _toggle_and_refresh(c, q, "as_document")

@Client.on_callback_query(filters.regex("^toggle_screenshots$"))
async def toggle_screenshots(c, q): await _toggle_and_refresh(c, q, "screenshots")

@Client.on_callback_query(filters.regex("^toggle_updates$"))
async def toggle_updates(c, q): await _toggle_and_refresh(c, q, "bot_updates")


# ── Thumbnail ────────────────────────────────────────────────────────────────
_waiting_thumb: set = set()


@Client.on_callback_query(filters.regex("^see_thumb$"))
async def see_thumb(client: Client, query: CallbackQuery):
    uid  = query.from_user.id
    u    = await db.get_user(uid)
    thumb = u.get("thumbnail") if u else None
    if thumb:
        await client.send_photo(query.message.chat.id, thumb, caption="🖼️ Your saved thumbnail")
    else:
        await query.answer("No thumbnail saved.", show_alert=True)


@Client.on_callback_query(filters.regex("^del_thumb$"))
async def del_thumb(client: Client, query: CallbackQuery):
    uid = query.from_user.id
    await db.del_thumbnail(uid)
    await query.answer("🗑️ Thumbnail deleted!", show_alert=True)


@Client.on_message(filters.command("setthumb") & filters.private)
async def set_thumb_cmd(client: Client, message: Message):
    uid = message.from_user.id
    if message.reply_to_message and message.reply_to_message.photo:
        file_id = message.reply_to_message.photo.file_id
        await db.set_thumbnail(uid, file_id)
        await message.reply_text("✅ Thumbnail saved!")
    else:
        _waiting_thumb.add(uid)
        await message.reply_text("📸 Send a photo to set as thumbnail:")


@Client.on_message(filters.private & filters.photo)
async def photo_received(client: Client, message: Message):
    uid = message.from_user.id
    if uid in _waiting_thumb:
        _waiting_thumb.discard(uid)
        file_id = message.photo.file_id
        await db.set_thumbnail(uid, file_id)
        await message.reply_text("✅ Thumbnail saved!")


# ── Timezone ─────────────────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^set_timezone$"))
async def set_timezone_cb(client: Client, query: CallbackQuery):
    rows = [[InlineKeyboardButton(tz, callback_data=f"tz#{tz}")] for tz in TIMEZONES]
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="open_settings")])
    await query.message.edit_text("🕒 Select your timezone:", reply_markup=InlineKeyboardMarkup(rows))
    await query.answer()


@Client.on_callback_query(filters.regex(r"^tz#"))
async def tz_chosen(client: Client, query: CallbackQuery):
    tz  = query.data.split("#", 1)[1]
    uid = query.from_user.id
    await db.set_timezone(uid, tz)
    await query.answer(f"✅ Timezone set to {tz}", show_alert=True)
    kb = await _settings_keyboard(uid)
    await query.message.edit_text(script.SETTINGS_TXT, reply_markup=kb)
