"""
Unified progress bar for uploads and downloads.
"""
import time
import asyncio
from utils import get_readable_file_size, get_readable_time, progress_bar


last_edit = {}   # message_id → timestamp


async def progress_callback(current: int, total: int, message, action: str = "Downloading"):
    """
    To be used as a progress callback in Pyrogram's download/upload.
    Throttles edits to once every 2 seconds.
    """
    now = time.time()
    mid = message.id
    if now - last_edit.get(mid, 0) < 2:
        return
    last_edit[mid] = now

    if total == 0:
        return

    elapsed = now - last_edit.get(f"{mid}_start", now)
    speed   = current / elapsed if elapsed > 0 else 0
    eta     = (total - current) / speed if speed > 0 else 0
    percent = current * 100 / total
    bar     = progress_bar(current, total)

    if action.lower() in ("downloading", "download"):
        emoji    = "⬇️"
        io_label = "📥 Downloaded"
    else:
        emoji    = "⬆️"
        io_label = "📤 Uploaded"

    text = (
        f"{emoji} <b>{action}...</b>\n"
        f"<code>{bar}</code>\n\n"
        f"📁 <b>Total Size :</b> <code>{get_readable_file_size(total)}</code>\n"
        f"{io_label} : <code>{get_readable_file_size(current)}</code>\n"
        f"📊 <b>Progress :</b> <code>{percent:.1f}%</code>\n"
        f"⚡ <b>Speed :</b> <code>{get_readable_file_size(int(speed))}/s</code>\n"
        f"⏳ <b>Remaining :</b> <code>{get_readable_time(eta)}</code>"
    )

    try:
        await message.edit(text)
    except Exception:
        pass


def make_progress(message, action: str):
    """Returns a (current, total) → coroutine callback bound to `message`."""
    last_edit[f"{message.id}_start"] = time.time()

    async def _cb(current: int, total: int):
        await progress_callback(current, total, message, action)

    return _cb
