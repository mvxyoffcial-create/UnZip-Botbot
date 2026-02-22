"""
Unified progress bar for uploads and downloads.
"""
import time
import asyncio
from utils import get_readable_file_size, get_readable_time


last_edit = {}   # message_id → timestamp


def create_progress_bar(current: int, total: int, length: int = 12) -> str:
    """Create a visual progress bar with filled and empty blocks."""
    if total <= 0:
        return "□" * length
    
    percentage = min(current / total, 1.0)
    filled = int(length * percentage)
    return "■" * filled + "□" * (length - filled)


async def progress_callback(
    current: int, 
    total: int, 
    message, 
    action: str = "Download",
    user_name: str = "User",
    user_id: int = 0
):
    """
    To be used as a progress callback in Pyrogram's download/upload.
    Throttles edits to once every 2 seconds.
    """
    now = time.time()
    mid = message.id
    
    # Throttle updates to once every 2 seconds
    if now - last_edit.get(mid, 0) < 2:
        return
    last_edit[mid] = now

    if total == 0:
        return

    # Calculate progress metrics
    start_time = last_edit.get(f"{mid}_start", now)
    elapsed = now - start_time
    speed = current / elapsed if elapsed > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    percent = (current * 100) / total
    
    # Create progress bar
    bar = create_progress_bar(current, total, length=12)

    # Build the status text with the new format
    text = (
        f"<code>[{bar}] {percent:.1f}%</code>\n"
        f"<b>┠ Processed:</b> <code>{get_readable_file_size(current)}</code> of <code>{get_readable_file_size(total)}</code>\n"
        f"<b>┠ Status:</b> <code>{action}</code> | ETA: <code>{get_readable_time(eta)}</code>\n"
        f"<b>┠ Speed:</b> <code>{get_readable_file_size(int(speed))}/s</code> | Elapsed: <code>{get_readable_time(elapsed)}</code>\n"
        f"<b>┠ Engine:</b> <code>Pyrogram</code>\n"
        f"<b>┠ User:</b> <code>{user_name}</code> | ID: <code>{user_id}</code>\n"
        f"<b>┖</b>"
    )

    try:
        await message.edit(text, disable_web_page_preview=True)
    except Exception:
        pass


def make_progress(message, action: str = "Download", user_name: str = "User", user_id: int = 0):
    """
    Returns a (current, total) → coroutine callback bound to `message`.
    
    Args:
        message: The Telegram message object to edit
        action: Action type (e.g., "Download", "Upload")
        user_name: Name of the user
        user_id: Telegram user ID
    """
    last_edit[f"{message.id}_start"] = time.time()

    async def _cb(current: int, total: int):
        await progress_callback(current, total, message, action, user_name, user_id)

    return _cb
