import os
import time
import asyncio
import aiohttp
import logging
from typing import Tuple, Optional

from pyrogram import Client
from pyrogram.errors import UserIsBlocked, InputUserDeactivated, PeerIdInvalid, FloodWait

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Temp state
# ──────────────────────────────────────────────────────────────────────────────
class temp:
    B_USERS_CANCEL  = False
    B_GROUPS_CANCEL = False
    B_LINK          = ""
    ME              = None           # bot info
    U_CLIENT        = None           # user Pyrogram client (session string)


# ──────────────────────────────────────────────────────────────────────────────
# Human-readable helpers
# ──────────────────────────────────────────────────────────────────────────────
def get_readable_file_size(size_in_bytes: int) -> str:
    """Convert bytes to human-readable format."""
    if size_in_bytes is None or size_in_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    index = 0
    size = float(size_in_bytes)
    
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    
    return f"{size:.2f} {units[index]}"


def get_readable_time(seconds: float) -> str:
    """Convert seconds to human-readable time format."""
    seconds = int(seconds)
    if seconds < 0:
        return "0s"
    
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    parts = []
    if days:    parts.append(f"{days}d")
    if hours:   parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    if secs or not parts:  # Always show seconds if nothing else
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def progress_bar(current: int, total: int, length: int = 12) -> str:
    """
    Generate a stylish progress bar string with filled and empty blocks.
    Uses ■ for filled and □ for empty.
    Default length is 12 to match the new format.
    """
    if total <= 0:
        return "□" * length
    
    percentage = min(current / total, 1.0)  # Cap at 100%
    filled = int(length * percentage)
    return "■" * filled + "□" * (length - filled)


def progress_bar_old(current: int, total: int, length: int = 20) -> str:
    """
    Legacy progress bar with █ and ░ characters.
    Kept for backward compatibility.
    """
    if total <= 0:
        return "░" * length
    
    percentage = min(current / total, 1.0)  # Cap at 100%
    filled = int(length * percentage)
    return "█" * filled + "░" * (length - filled)


# ──────────────────────────────────────────────────────────────────────────────
# Time string → seconds (no need for async)
# ──────────────────────────────────────────────────────────────────────────────
def get_seconds(time_str: str) -> int:
    """Convert time string like '5 mins' to seconds."""
    mapping = {
        "sec": 1, "secs": 1, "second": 1, "seconds": 1,
        "min": 60, "mins": 60, "minute": 60, "minutes": 60,
        "hour": 3600, "hours": 3600, "hr": 3600, "hrs": 3600,
        "day": 86400, "days": 86400,
        "week": 604800, "weeks": 604800,
        "month": 2592000, "months": 2592000,
        "year": 31536000, "years": 31536000,
    }
    
    parts = time_str.lower().strip().split()
    if len(parts) != 2:
        return 0
    
    try:
        value = int(parts[0])
        if value < 0:
            return 0
        multiplier = mapping.get(parts[1], 0)
        return value * multiplier
    except ValueError:
        return 0


# ──────────────────────────────────────────────────────────────────────────────
# Welcome image — fixed URL from config.py (WELCOME_IMAGE)
# ──────────────────────────────────────────────────────────────────────────────
def get_welcome_image() -> str:
    """Get welcome image URL from config."""
    from config import Config
    return Config.WELCOME_IMAGE


# ──────────────────────────────────────────────────────────────────────────────
# Force-subscribe check (optimized with concurrent checks)
# ──────────────────────────────────────────────────────────────────────────────
async def check_force_sub(client: Client, user_id: int, channels: list) -> list:
    """Returns list of channel usernames the user has NOT joined."""
    
    async def check_single_channel(ch: str) -> Optional[str]:
        """Check if user is in a single channel. Returns channel if not joined."""
        try:
            member = await client.get_chat_member(ch, user_id)
            if member.status.value in ("left", "banned", "kicked"):
                return ch
        except Exception:
            return ch
        return None
    
    # Run all checks concurrently for speed
    tasks = [check_single_channel(ch) for ch in channels]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out None values and exceptions
    not_joined = [ch for ch in results if ch and not isinstance(ch, Exception)]
    return not_joined


# ──────────────────────────────────────────────────────────────────────────────
# Broadcast helpers
# ──────────────────────────────────────────────────────────────────────────────
async def users_broadcast(user_id: int, message, pin: bool = False) -> Tuple[bool, str]:
    """Broadcast message to a single user."""
    try:
        sent = await message.copy(chat_id=user_id)
        if pin:
            try:
                await sent.pin(disable_notification=True)
            except Exception:
                pass
        return True, "Success"
    except UserIsBlocked:
        return False, "Blocked"
    except InputUserDeactivated:
        return False, "Deleted"
    except PeerIdInvalid:
        return False, "Deleted"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await users_broadcast(user_id, message, pin)
    except Exception as e:
        log.exception(f"Broadcast error for {user_id}: {e}")
        return False, "Error"


async def groups_broadcast(chat_id: int, message, pin: bool = False) -> str:
    """Broadcast message to a group."""
    try:
        sent = await message.copy(chat_id=chat_id)
        if pin:
            try:
                await sent.pin(disable_notification=True)
            except Exception:
                pass
        return "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await groups_broadcast(chat_id, message, pin)
    except Exception as e:
        log.exception(f"Group broadcast error for {chat_id}: {e}")
        return "Error"


async def clear_junk(user_id: int, message) -> Tuple[bool, str]:
    """Send message to user and return status."""
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except UserIsBlocked:
        return False, "Blocked"
    except InputUserDeactivated:
        return False, "Deleted"
    except Exception:
        return False, "Error"


async def junk_group(chat_id: int, message) -> Tuple[bool, str, str]:
    """Send message to group and return status."""
    try:
        await message.copy(chat_id=chat_id)
        return True, "ok", ""
    except Exception as e:
        return False, "deleted", str(e) + "\n"


# ──────────────────────────────────────────────────────────────────────────────
# Download helpers (optimized chunk size and error handling)
# ──────────────────────────────────────────────────────────────────────────────
async def download_url(url: str, dest: str, progress_callback=None) -> str:
    """
    Download a direct URL file to dest directory. Returns local path.
    Optimized with larger chunk size and better error handling.
    """
    os.makedirs(dest, exist_ok=True)
    
    # Extract filename from URL, remove query params
    filename = url.split("?")[0].split("/")[-1] or "downloaded_file"
    local_path = os.path.join(dest, filename)

    connector = aiohttp.TCPConnector(limit=10)
    timeout = aiohttp.ClientTimeout(total=None, connect=30)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.get(url, timeout=timeout) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("Content-Length", 0))
                done = 0
                start = time.time()

                # Use larger chunk size for faster downloads (256KB)
                with open(local_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(262144):
                        f.write(chunk)
                        done += len(chunk)
                        
                        if progress_callback:
                            elapsed = time.time() - start
                            speed = done / elapsed if elapsed > 0 else 0
                            eta = (total - done) / speed if speed > 0 else 0
                            await progress_callback(done, total, speed, eta)
        
        except aiohttp.ClientError as e:
            log.error(f"Download failed for {url}: {e}")
            # Clean up partial file
            if os.path.exists(local_path):
                os.remove(local_path)
            raise
        except Exception as e:
            log.exception(f"Unexpected error downloading {url}: {e}")
            if os.path.exists(local_path):
                os.remove(local_path)
            raise

    return local_path


# ──────────────────────────────────────────────────────────────────────────────
# Formatted progress text generator (new stylish format)
# ──────────────────────────────────────────────────────────────────────────────
def get_progress_text(
    current: int,
    total: int,
    speed: float,
    eta: float,
    status: str = "Processing",
    engine: str = "System",
    user_name: str = "User",
    user_id: int = 0,
    elapsed: float = 0
) -> str:
    """
    Generate stylish progress text in the new format.
    
    Args:
        current: Current progress in bytes
        total: Total size in bytes
        speed: Speed in bytes/second
        eta: Estimated time remaining in seconds
        status: Status text (e.g., "Download", "Upload", "Extracting")
        engine: Engine name (e.g., "Pyrogram", "Archive Extractor")
        user_name: Name of the user
        user_id: Telegram user ID
        elapsed: Elapsed time in seconds
    
    Returns:
        Formatted progress text string
    """
    percent = (current * 100) / total if total > 0 else 0
    bar = progress_bar(current, total, length=12)
    
    text = (
        f"<code>[{bar}] {percent:.1f}%</code>\n"
        f"<b>┠ Processed:</b> <code>{get_readable_file_size(current)}</code> of <code>{get_readable_file_size(total)}</code>\n"
        f"<b>┠ Status:</b> <code>{status}</code> | ETA: <code>{get_readable_time(eta)}</code>\n"
        f"<b>┠ Speed:</b> <code>{get_readable_file_size(int(speed))}/s</code> | Elapsed: <code>{get_readable_time(elapsed)}</code>\n"
        f"<b>┠ Engine:</b> <code>{engine}</code>\n"
        f"<b>┠ User:</b> <code>{user_name}</code> | ID: <code>{user_id}</code>\n"
        f"<b>┖</b>"
    )
    
    return text
