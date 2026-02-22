import os
import asyncio
import subprocess
import pytz
import logging
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from config import Config
from database import db
from script import script

log = logging.getLogger(__name__)

TIMEZONES = ["Asia/Kolkata", "UTC", "US/Eastern", "US/Pacific", "Europe/London", "Asia/Dubai"]

# Directory to store user thumbnails
THUMB_DIR = os.path.join(Config.DOWNLOAD_DIR, "thumbnails")
os.makedirs(THUMB_DIR, exist_ok=True)

# Directory to store screenshots
SCREENSHOT_DIR = os.path.join(Config.DOWNLOAD_DIR, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

SCREENSHOT_COUNT = 10   # Number of screenshots to capture


def _on_off(val: bool) -> str:
    return "✅ ON" if val else "❌ OFF"


def get_user_thumb_path(user_id: int) -> str:
    """Get the local path for a user's thumbnail"""
    return os.path.join(THUMB_DIR, f"thumb_{user_id}.jpg")


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
    thumb_path = u.get("thumbnail") if u else None
    
    if thumb_path and os.path.exists(thumb_path):
        try:
            await client.send_photo(query.message.chat.id, thumb_path, caption="🖼️ Your saved thumbnail")
            await query.answer("✅ Thumbnail displayed!")
        except Exception as e:
            log.error(f"Error showing thumbnail: {e}")
            await query.answer("❌ Error displaying thumbnail!", show_alert=True)
    else:
        await query.answer("❌ No thumbnail saved.", show_alert=True)


@Client.on_callback_query(filters.regex("^del_thumb$"))
async def del_thumb(client: Client, query: CallbackQuery):
    uid = query.from_user.id
    
    u = await db.get_user(uid)
    thumb_path = u.get("thumbnail") if u else None
    
    await db.del_thumbnail(uid)
    
    if thumb_path and os.path.exists(thumb_path):
        try:
            os.remove(thumb_path)
            log.info(f"Deleted thumbnail file for user {uid}")
        except Exception as e:
            log.warning(f"Could not delete thumbnail file: {e}")
    
    await query.answer("🗑️ Thumbnail deleted!", show_alert=True)


@Client.on_message(filters.command("setthumb") & filters.private)
async def set_thumb_cmd(client: Client, message: Message):
    uid = message.from_user.id
    
    if message.reply_to_message and message.reply_to_message.photo:
        status_msg = await message.reply_text("⏳ Downloading thumbnail...")
        
        try:
            thumb_path = get_user_thumb_path(uid)
            await message.reply_to_message.download(file_name=thumb_path)
            await db.set_thumbnail(uid, thumb_path)
            await status_msg.edit_text("✅ Thumbnail saved!")
        except Exception as e:
            log.error(f"Error saving thumbnail for user {uid}: {e}")
            await status_msg.edit_text(f"❌ Error: {str(e)}")
    else:
        _waiting_thumb.add(uid)
        await message.reply_text(
            "📸 **Set Custom Thumbnail**\n\n"
            "Send me a photo to set as your custom thumbnail.\n\n"
            "Or reply to a photo with /setthumb"
        )


@Client.on_message(filters.private & filters.photo)
async def photo_received(client: Client, message: Message):
    uid = message.from_user.id
    
    if uid in _waiting_thumb:
        _waiting_thumb.discard(uid)
        
        status_msg = await message.reply_text("⏳ Downloading thumbnail...")
        
        try:
            thumb_path = get_user_thumb_path(uid)
            await message.download(file_name=thumb_path)
            await db.set_thumbnail(uid, thumb_path)
            await status_msg.edit_text(
                "✅ **Thumbnail Saved!**\n\n"
                "Your custom thumbnail has been set successfully.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("👁️ View", callback_data="see_thumb"),
                    InlineKeyboardButton("🗑️ Delete", callback_data="del_thumb")
                ]])
            )
        except Exception as e:
            log.error(f"Error saving thumbnail for user {uid}: {e}")
            await status_msg.edit_text(f"❌ Error: {str(e)}")


# ── Screenshot ───────────────────────────────────────────────────────────────

def _get_video_duration(video_path: str) -> float:
    """Use ffprobe to get video duration in seconds."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def _take_screenshots(video_path: str, out_dir: str, count: int = SCREENSHOT_COUNT) -> list[str]:
    """
    Extract `count` evenly-spaced screenshots from the video using ffmpeg.
    Returns a list of saved image paths.
    """
    duration = _get_video_duration(video_path)
    if duration <= 0:
        raise ValueError("Could not determine video duration.")

    # Space screenshots evenly, avoiding the very start/end
    interval = duration / (count + 1)
    paths = []

    for i in range(1, count + 1):
        timestamp = interval * i
        out_path  = os.path.join(out_dir, f"screenshot_{i:02d}.jpg")
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",          # high quality JPEG
            out_path,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0 and os.path.exists(out_path):
            paths.append(out_path)
        else:
            log.warning(f"ffmpeg failed for screenshot {i}: {result.stderr.decode()[-200:]}")

    return paths


@Client.on_message(filters.command("screenshot") & filters.private)
async def screenshot_cmd(client: Client, message: Message):
    """
    Reply to a video message with /screenshot to get 10 evenly-spaced screenshots.
    Only works for video files — documents and audio are rejected.
    """
    uid    = message.from_user.id
    reply  = message.reply_to_message

    # ── Guard: must reply to a video ────────────────────────────────────────
    if not reply:
        return await message.reply_text(
            "📽️ **How to use:**\n"
            "Reply to a **video** message with /screenshot\n\n"
            "ℹ️ This command only works for videos."
        )

    is_video = bool(reply.video)
    # Also accept video sent as document (mp4/mkv files sent without compression)
    is_video_doc = (
        reply.document
        and reply.document.mime_type
        and reply.document.mime_type.startswith("video/")
    )

    if not (is_video or is_video_doc):
        return await message.reply_text(
            "❌ **Videos only!**\n\n"
            "Please reply to a **video** message.\n"
            "This command does not work for photos, audio, or other files."
        )

    media    = reply.video or reply.document
    fname    = media.file_name or "video"
    fsize    = media.file_size or 0

    status = await message.reply_text(
        f"⬇️ Downloading video to generate screenshots...\n"
        f"📁 **File:** `{fname}`"
    )

    # ── Download ─────────────────────────────────────────────────────────────
    dl_dir  = os.path.join(Config.DOWNLOAD_DIR, str(uid), "screenshot_input")
    out_dir = os.path.join(SCREENSHOT_DIR, str(uid))
    os.makedirs(dl_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    # Clean old screenshots for this user
    for f in os.listdir(out_dir):
        try:
            os.remove(os.path.join(out_dir, f))
        except Exception:
            pass

    try:
        local_path = await client.download_media(
            reply,
            file_name=os.path.join(dl_dir, fname),
        )
    except Exception as e:
        return await status.edit(f"❌ Download failed!\n`{e}`")

    await status.edit(f"🎬 Taking {SCREENSHOT_COUNT} screenshots... please wait.")

    # ── Extract screenshots in thread (blocking ffmpeg calls) ─────────────
    loop = asyncio.get_event_loop()
    try:
        shot_paths = await loop.run_in_executor(
            None,
            lambda: _take_screenshots(local_path, out_dir, SCREENSHOT_COUNT)
        )
    except Exception as e:
        await status.edit(f"❌ Screenshot extraction failed!\n`{e}`")
        try:
            os.remove(local_path)
        except Exception:
            pass
        return

    # Cleanup downloaded video
    try:
        os.remove(local_path)
    except Exception:
        pass

    if not shot_paths:
        return await status.edit("❌ No screenshots could be generated. Is the file a valid video?")

    await status.edit(f"📤 Sending {len(shot_paths)} screenshots...")

    # ── Send as media group (max 10 per group) ────────────────────────────
    from pyrogram.types import InputMediaPhoto

    media_group = [
        InputMediaPhoto(
            media=p,
            caption=f"🎬 Screenshot {i+1}/{len(shot_paths)}" if i == 0 else ""
        )
        for i, p in enumerate(shot_paths)
    ]

    try:
        await client.send_media_group(message.chat.id, media_group)
        await status.edit(f"✅ Done! Sent **{len(shot_paths)} screenshots**.")
    except Exception as e:
        log.error(f"Error sending screenshots: {e}")
        # Fallback: send one by one
        await status.edit(f"📤 Sending screenshots one by one...")
        for i, path in enumerate(shot_paths, 1):
            try:
                await client.send_photo(
                    message.chat.id,
                    path,
                    caption=f"🎬 Screenshot {i}/{len(shot_paths)}"
                )
            except Exception as ex:
                log.warning(f"Failed to send screenshot {i}: {ex}")
        await status.edit(f"✅ Done! Sent **{len(shot_paths)} screenshots**.")

    # Cleanup screenshots
    for p in shot_paths:
        try:
            os.remove(p)
        except Exception:
            pass


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
