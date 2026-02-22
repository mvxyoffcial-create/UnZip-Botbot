"""
Core unzip plugin with auto-filter (inline file selection after extraction).
"""
import os
import shutil
import asyncio
import logging
import time
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from config import Config
from database import db
from script import script
from utils import get_readable_file_size, check_force_sub, temp
from helper.extractor import extract_archive, is_archive
from helper.uploader import upload_file
from helper.progress import make_progress

log = logging.getLogger(__name__)

# In-memory state: user_id → extraction session
_sessions: dict = {}   # user_id → {"files": [...], "dest": str, "selected": set}

FORCE_CHANNELS = Config.FORCE_SUB_CHANNELS


# ──────────────────────────────────────────────────────────────────────────────
# Helper: check limit
# ──────────────────────────────────────────────────────────────────────────────
async def _check_limit(client, message: Message, file_size: int) -> bool:
    uid      = message.from_user.id
    premium  = await db.is_premium(uid) or uid == Config.OWNER_ID
    limit    = Config.PREMIUM_LIMIT if premium else Config.FREE_LIMIT
    if file_size > limit:
        label = get_readable_file_size(limit)
        await message.reply_text(
            f"❌ File too large!\n"
            f"{'💎 Premium' if premium else '🆓 Free'} limit: **{label}**\n"
            f"{'Upgrade to Premium for 4 GB!' if not premium else ''}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("💎 Get Premium", callback_data="premium_info")
            ]]) if not premium else None
        )
        return False
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Guard: force-sub
# ──────────────────────────────────────────────────────────────────────────────
async def _guard(client, message: Message) -> bool:
    uid     = message.from_user.id
    missing = await check_force_sub(client, uid, FORCE_CHANNELS)
    if missing:
        rows = [[InlineKeyboardButton(f"Join @{ch}", url=f"https://t.me/{ch}")] for ch in missing]
        rows.append([InlineKeyboardButton("✅ I've Joined", callback_data="check_sub")])
        await message.reply_photo(
            photo=Config.FORCE_IMAGE,
            caption="Please join our channels first!",
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return False
    if await db.is_banned(uid):
        await message.reply_text("🚫 You are banned.")
        return False
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Rename helper
# ──────────────────────────────────────────────────────────────────────────────
_rename_pending: dict = {}   # user_id → {"msg_id": int, "path": str, "action": str}


async def _ask_rename(client: Client, message: Message, path: str, action: str):
    uid = message.from_user.id
    _rename_pending[uid] = {"path": path, "action": action, "orig_msg": message, "prompt_id": None}
    sent = await message.reply_text(
        script.RENAME_TXT,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭ Skip", callback_data=f"skip_rename#{uid}")
        ]])
    )
    # Guard: entry may have been popped by a concurrent handler while we were awaiting
    if uid in _rename_pending:
        _rename_pending[uid]["prompt_id"] = sent.id


@Client.on_callback_query(filters.regex(r"^skip_rename#"))
async def skip_rename_cb(client: Client, query: CallbackQuery):
    uid = int(query.data.split("#")[1])
    if uid != query.from_user.id:
        return
    data = _rename_pending.pop(uid, None)
    if data:
        await query.message.delete()
        await _process_archive(client, data["orig_msg"], data["path"])


@Client.on_message(filters.private & filters.text & ~filters.command("start"))
async def rename_reply_handler(client: Client, message: Message):
    uid = message.from_user.id
    if uid not in _rename_pending:
        return
    data    = _rename_pending.pop(uid)
    new_name = message.text.strip()
    if new_name.lower() == "/skip":
        new_name = None

    path = data["path"]
    if new_name:
        ext      = os.path.splitext(path)[1]
        new_path = os.path.join(os.path.dirname(path), new_name + ext)
        os.rename(path, new_path)
        path = new_path

    try:
        if data.get("prompt_id"):
            await client.delete_messages(message.chat.id, data["prompt_id"])
    except Exception:
        pass
    await _process_archive(client, data["orig_msg"], path)


# ──────────────────────────────────────────────────────────────────────────────
# File received handler
# ──────────────────────────────────────────────────────────────────────────────
@Client.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def file_received(client: Client, message: Message):
    if not await _guard(client, message):
        return

    uid  = message.from_user.id
    doc  = message.document or message.video or message.audio
    fname = (doc.file_name or "file") if doc else "file"
    fsize = doc.file_size if doc else 0

    if not is_archive(fname):
        await message.reply_text(
            "📦 This doesn't look like a supported archive.\n"
            "Supported: ZIP, RAR, 7Z, TAR, TAR.GZ, TAR.BZ2, TAR.XZ"
        )
        return

    if not await _check_limit(client, message, fsize):
        return

    # Get user info for progress
    user_name = message.from_user.first_name or "User"
    user_id = message.from_user.id

    # Rename option
    u_data = await db.get_user(uid)
    if u_data and u_data.get("rename", True):
        dest = os.path.join(Config.DOWNLOAD_DIR, str(uid), fname)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        status = await message.reply_text("⏳ Waiting for new filename...")
        # Download first then ask rename
        await status.edit("⬇️ Downloading...")
        local = await client.download_media(
            message,
            file_name=dest,
            progress=make_progress(status, "Download", user_name, user_id),
        )
        await status.delete()
        await _ask_rename(client, message, local, "unzip")
    else:
        status = await message.reply_text("⬇️ Downloading...")
        dest   = os.path.join(Config.DOWNLOAD_DIR, str(uid), fname)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        local  = await client.download_media(
            message,
            file_name=dest,
            progress=make_progress(status, "Download", user_name, user_id),
        )
        await status.delete()
        await _process_archive(client, message, local)


# ──────────────────────────────────────────────────────────────────────────────
# Progress bar helper
# ──────────────────────────────────────────────────────────────────────────────
def create_progress_bar(current: int, total: int, length: int = 12) -> str:
    """Create a visual progress bar with filled and empty blocks."""
    if total <= 0:
        return "□" * length
    
    percentage = min(current / total, 1.0)
    filled = int(length * percentage)
    return "■" * filled + "□" * (length - filled)


# ──────────────────────────────────────────────────────────────────────────────
# Extraction helpers with progress bar
# ──────────────────────────────────────────────────────────────────────────────

async def _get_total_uncompressed(archive_path: str):
    """Try to obtain total uncompressed size of all files inside the archive."""
    ext = os.path.splitext(archive_path)[1].lower()
    total = None
    try:
        if ext == '.zip':
            import zipfile
            with zipfile.ZipFile(archive_path, 'r') as z:
                total = sum(f.file_size for f in z.infolist())
        elif ext in ('.rar', '.cbr'):
            import rarfile
            with rarfile.RarFile(archive_path, 'r') as r:
                total = sum(f.file_size for f in r.infolist())
        elif ext in ('.7z', '.cb7'):
            import py7zr
            with py7zr.SevenZipFile(archive_path, 'r') as sz:
                total = sum(f.uncompressed for f in sz.list())
        elif ext in ('.tar', '.tgz', '.tar.gz', '.tbz2', '.tar.bz2', '.txz', '.tar.xz'):
            import tarfile
            with tarfile.open(archive_path, 'r') as tar:
                total = sum(f.size for f in tar.getmembers() if f.isfile())
    except Exception as e:
        log.debug(f"Could not get uncompressed size: {e}")
    return total


def _extract_sync(archive_path: str, dest_dir: str):
    """Synchronous extraction that works with both async and sync extractors."""
    try:
        import asyncio
        from helper.extractor import extract_archive as async_extract
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(async_extract(archive_path, dest_dir))
        loop.close()
        return result
    except Exception:
        return extract_archive(archive_path, dest_dir)


async def _process_archive(client: Client, message: Message, archive_path: str):
    uid = message.from_user.id
    user_name = message.from_user.first_name or "User"
    
    status = await message.reply_text("📦 Extracting archive...")
    dest_dir = os.path.join(Config.DOWNLOAD_DIR, str(uid), "extracted")
    os.makedirs(dest_dir, exist_ok=True)

    # Try to get total size
    total_size = await _get_total_uncompressed(archive_path)

    start_time = time.time()
    last_update = [0]  # Use list to allow modification in nested function

    async def update_progress():
        """Periodically update extraction progress."""
        while True:
            await asyncio.sleep(2)  # Update every 2 seconds
            elapsed = time.time() - start_time
            
            # Get current extracted size
            try:
                current_size = sum(
                    os.path.getsize(os.path.join(root, f))
                    for root, _, files in os.walk(dest_dir)
                    for f in files
                )
            except Exception:
                current_size = 0

            if total_size and total_size > 0:
                percent = min((current_size * 100) / total_size, 99.9)
                bar = create_progress_bar(current_size, total_size, length=12)
                eta = ((total_size - current_size) / (current_size / elapsed)) if current_size > 0 else 0
                
                text = (
                    f"<code>[{bar}] {percent:.1f}%</code>\n"
                    f"<b>┠ Processed:</b> <code>{get_readable_file_size(current_size)}</code> of <code>{get_readable_file_size(total_size)}</code>\n"
                    f"<b>┠ Status:</b> <code>Extracting</code> | ETA: <code>{int(eta)}s</code>\n"
                    f"<b>┠ Speed:</b> <code>{get_readable_file_size(int(current_size / elapsed))}/s</code> | Elapsed: <code>{int(elapsed)}s</code>\n"
                    f"<b>┠ Engine:</b> <code>Archive Extractor</code>\n"
                    f"<b>┠ User:</b> <code>{user_name}</code> | ID: <code>{uid}</code>\n"
                    f"<b>┖</b>"
                )
            else:
                # No total size available, show indeterminate progress
                bar = "■" * (int(elapsed) % 12) + "□" * (12 - (int(elapsed) % 12))
                text = (
                    f"<code>[{bar}] Processing...</code>\n"
                    f"<b>┠ Extracted:</b> <code>{get_readable_file_size(current_size)}</code>\n"
                    f"<b>┠ Status:</b> <code>Extracting</code>\n"
                    f"<b>┠ Speed:</b> <code>{get_readable_file_size(int(current_size / elapsed))}/s</code> | Elapsed: <code>{int(elapsed)}s</code>\n"
                    f"<b>┠ Engine:</b> <code>Archive Extractor</code>\n"
                    f"<b>┠ User:</b> <code>{user_name}</code> | ID: <code>{uid}</code>\n"
                    f"<b>┖</b>"
                )

            try:
                await status.edit(text, disable_web_page_preview=True)
            except Exception:
                pass

    # Start progress updater task
    progress_task = asyncio.create_task(update_progress())

    try:
        # Run extraction in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        files = await loop.run_in_executor(None, _extract_sync, archive_path, dest_dir)
    except Exception as e:
        progress_task.cancel()
        await status.edit(f"❌ Extraction failed!\n`{e}`")
        shutil.rmtree(dest_dir, ignore_errors=True)
        os.remove(archive_path)
        return
    finally:
        progress_task.cancel()
        try:
            await progress_task
        except asyncio.CancelledError:
            pass

    # Cleanup archive
    try:
        os.remove(archive_path)
    except Exception:
        pass

    if not files:
        await status.edit("❌ Archive is empty or extraction failed.")
        shutil.rmtree(dest_dir, ignore_errors=True)
        return

    # Store session
    _sessions[uid] = {
        "files":    files,
        "dest":     dest_dir,
        "selected": set(range(len(files))),  # all selected by default
        "msg":      message,
        "status":   status,
    }

    await status.edit(
        script.EXTRACT_CHOICE_TXT.format(count=len(files)),
        reply_markup=_build_filter_keyboard(uid),
    )


def _build_filter_keyboard(uid: int) -> InlineKeyboardMarkup:
    sess  = _sessions.get(uid, {})
    files = sess.get("files", [])
    sel   = sess.get("selected", set())
    rows  = []

    for i, path in enumerate(files):
        name  = os.path.basename(path)
        size  = get_readable_file_size(os.path.getsize(path))
        tick  = "✅" if i in sel else "☐"
        rows.append([InlineKeyboardButton(
            f"{tick} {name} ({size})",
            callback_data=f"toggle_file#{uid}#{i}"
        )])

    # Control row
    rows.append([
        InlineKeyboardButton("☑️ All",          callback_data=f"sel_all#{uid}"),
        InlineKeyboardButton("🔲 None",          callback_data=f"sel_none#{uid}"),
    ])
    rows.append([
        InlineKeyboardButton("⬆️ Upload Selected", callback_data=f"upload_sel#{uid}"),
        InlineKeyboardButton("🗑️ Cancel",           callback_data=f"cancel_ext#{uid}"),
    ])
    return InlineKeyboardMarkup(rows)


@Client.on_callback_query(filters.regex(r"^toggle_file#"))
async def toggle_file_cb(client: Client, query: CallbackQuery):
    _, uid_s, idx_s = query.data.split("#")
    uid = int(uid_s)
    if query.from_user.id != uid:
        return
    idx = int(idx_s)
    sess = _sessions.get(uid)
    if not sess:
        return await query.answer("Session expired.", show_alert=True)
    if idx in sess["selected"]:
        sess["selected"].discard(idx)
    else:
        sess["selected"].add(idx)
    await query.message.edit_reply_markup(_build_filter_keyboard(uid))
    await query.answer()


@Client.on_callback_query(filters.regex(r"^sel_all#"))
async def sel_all_cb(client: Client, query: CallbackQuery):
    uid = int(query.data.split("#")[1])
    if query.from_user.id != uid:
        return
    sess = _sessions.get(uid)
    if sess:
        sess["selected"] = set(range(len(sess["files"])))
        await query.message.edit_reply_markup(_build_filter_keyboard(uid))
    await query.answer("All selected")


@Client.on_callback_query(filters.regex(r"^sel_none#"))
async def sel_none_cb(client: Client, query: CallbackQuery):
    uid = int(query.data.split("#")[1])
    if query.from_user.id != uid:
        return
    sess = _sessions.get(uid)
    if sess:
        sess["selected"] = set()
        await query.message.edit_reply_markup(_build_filter_keyboard(uid))
    await query.answer("All deselected")


@Client.on_callback_query(filters.regex(r"^cancel_ext#"))
async def cancel_ext_cb(client: Client, query: CallbackQuery):
    uid = int(query.data.split("#")[1])
    if query.from_user.id != uid:
        return
    sess = _sessions.pop(uid, None)
    if sess:
        shutil.rmtree(sess["dest"], ignore_errors=True)
    await query.message.edit("❌ Cancelled.")
    await query.answer()


@Client.on_callback_query(filters.regex(r"^upload_sel#"))
async def upload_selected_cb(client: Client, query: CallbackQuery):
    uid = int(query.data.split("#")[1])
    if query.from_user.id != uid:
        return
    sess = _sessions.pop(uid, None)
    if not sess:
        return await query.answer("Session expired.", show_alert=True)

    selected = sorted(sess["selected"])
    if not selected:
        return await query.answer("No files selected!", show_alert=True)

    await query.message.edit("⬆️ Uploading selected files...")
    u_data   = await db.get_user(uid)
    thumb    = u_data.get("thumbnail") if u_data else None
    spoiler  = u_data.get("spoiler", False) if u_data else False
    as_doc   = u_data.get("as_document", False) if u_data else False

    # Get user info for progress
    user_name = query.from_user.first_name or "User"

    for i in selected:
        fpath = sess["files"][i]
        fname = os.path.basename(fpath)
        status = await query.message.reply_text(f"⬆️ Uploading `{fname}`...")
        try:
            await upload_file(
                bot=client,
                chat_id=query.message.chat.id,
                file_path=fpath,
                caption=f"📄 `{fname}`",
                thumb=thumb,
                as_document=as_doc,
                spoiler=spoiler,
                status_msg=status,
                user_name=user_name,
                user_id=uid,
            )
            await status.delete()
        except Exception as e:
            await status.edit(f"❌ Failed to upload `{fname}`\n`{e}`")

    shutil.rmtree(sess["dest"], ignore_errors=True)
    await query.message.edit("✅ All selected files uploaded!")


# ──────────────────────────────────────────────────────────────────────────────
# Direct link download
# ──────────────────────────────────────────────────────────────────────────────
@Client.on_message(filters.private & filters.regex(r"^https?://\S+$"))
async def url_download(client: Client, message: Message):
    if not await _guard(client, message):
        return

    url = message.text.strip()
    uid = message.from_user.id
    user_name = message.from_user.first_name or "User"
    u_data = await db.get_user(uid)

    status = await message.reply_text("⬇️ Downloading from URL...")
    dest   = os.path.join(Config.DOWNLOAD_DIR, str(uid))
    os.makedirs(dest, exist_ok=True)

    from utils import download_url

    async def _prog(done, total, speed, eta):
        bar = create_progress_bar(done, total, length=12)
        elapsed = time.time() - _prog.start_time
        percent = (done * 100) / total if total > 0 else 0
        
        text = (
            f"<code>[{bar}] {percent:.1f}%</code>\n"
            f"<b>┠ Processed:</b> <code>{get_readable_file_size(done)}</code> of <code>{get_readable_file_size(total)}</code>\n"
            f"<b>┠ Status:</b> <code>Download</code> | ETA: <code>{int(eta)}s</code>\n"
            f"<b>┠ Speed:</b> <code>{get_readable_file_size(int(speed))}/s</code> | Elapsed: <code>{int(elapsed)}s</code>\n"
            f"<b>┠ Engine:</b> <code>Direct URL</code>\n"
            f"<b>┠ User:</b> <code>{user_name}</code> | ID: <code>{uid}</code>\n"
            f"<b>┖</b>"
        )
        
        try:
            await status.edit(text, disable_web_page_preview=True)
        except Exception:
            pass

    _prog.start_time = time.time()

    try:
        local = await download_url(url, dest, _prog)
    except Exception as e:
        return await status.edit(f"❌ Download failed!\n`{e}`")

    fsize = os.path.getsize(local)
    if not await _check_limit(client, message, fsize):
        os.remove(local)
        return

    if is_archive(local):
        await status.delete()
        await _process_archive(client, message, local)
    else:
        # Ask rename if enabled
        if u_data and u_data.get("rename", True):
            await status.delete()
            await _ask_rename(client, message, local, "upload")
        else:
            thumb   = u_data.get("thumbnail") if u_data else None
            spoiler = u_data.get("spoiler", False) if u_data else False
            as_doc  = u_data.get("as_document", False) if u_data else False
            fname   = os.path.basename(local)
            await status.edit(f"⬆️ Uploading `{fname}`...")
            try:
                await upload_file(
                    bot=client,
                    chat_id=message.chat.id,
                    file_path=local,
                    caption=f"📄 `{fname}`",
                    thumb=thumb,
                    as_document=as_doc,
                    spoiler=spoiler,
                    status_msg=status,
                    user_name=user_name,
                    user_id=uid,
                )
                await status.delete()
                os.remove(local)
            except Exception as e:
                await status.edit(f"❌ Upload failed!\n`{e}`")
