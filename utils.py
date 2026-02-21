import os
import time
import math
import asyncio
import aiohttp
import datetime
import logging
from typing import Tuple

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
    if size_in_bytes is None:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} PB"


def get_readable_time(seconds: float) -> str:
    seconds = int(seconds)
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days:    parts.append(f"{days}d")
    if hours:   parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def progress_bar(current: int, total: int, length: int = 20) -> str:
    if total == 0:
        return "░" * length
    filled = int(length * current / total)
    return "█" * filled + "░" * (length - filled)


# ──────────────────────────────────────────────────────────────────────────────
# Time string → seconds
# ──────────────────────────────────────────────────────────────────────────────
async def get_seconds(time_str: str) -> int:
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
        multiplier = mapping.get(parts[1], 0)
        return value * multiplier
    except ValueError:
        return 0


# ──────────────────────────────────────────────────────────────────────────────
# Random anime wallpaper
# ──────────────────────────────────────────────────────────────────────────────
async def get_welcome_image() -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.aniwallpaper.workers.dev/random?type=girl",
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("url") or data.get("image") or ""
    except Exception:
        pass
    return "https://i.ibb.co/pr2H8cwT/img-8312532076.jpg"


# ──────────────────────────────────────────────────────────────────────────────
# Force-subscribe check
# ──────────────────────────────────────────────────────────────────────────────
async def check_force_sub(client: Client, user_id: int, channels: list) -> list:
    """Returns list of channel usernames the user has NOT joined."""
    not_joined = []
    for ch in channels:
        try:
            member = await client.get_chat_member(ch, user_id)
            if member.status.value in ("left", "banned", "kicked"):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return not_joined


# ──────────────────────────────────────────────────────────────────────────────
# Broadcast helpers
# ──────────────────────────────────────────────────────────────────────────────
async def users_broadcast(user_id: int, message, pin: bool = False) -> Tuple[bool, str]:
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
    try:
        await message.copy(chat_id=chat_id)
        return True, "ok", ""
    except Exception as e:
        return False, "deleted", str(e) + "\n"


# ──────────────────────────────────────────────────────────────────────────────
# Download helpers
# ──────────────────────────────────────────────────────────────────────────────
async def download_url(url: str, dest: str, progress_callback=None) -> str:
    """Download a direct URL file to dest directory. Returns local path."""
    os.makedirs(dest, exist_ok=True)
    filename = url.split("?")[0].split("/")[-1] or "downloaded_file"
    local_path = os.path.join(dest, filename)

    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=None)) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", 0))
            done  = 0
            start = time.time()

            with open(local_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 64):
                    f.write(chunk)
                    done += len(chunk)
                    if progress_callback:
                        elapsed = time.time() - start
                        speed   = done / elapsed if elapsed > 0 else 0
                        eta     = (total - done) / speed if speed > 0 else 0
                        await progress_callback(done, total, speed, eta)

    return local_path
