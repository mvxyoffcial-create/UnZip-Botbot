import os
import mimetypes
import tempfile
import logging
from pyrogram import Client
from helper.progress import make_progress
from utils import temp

log = logging.getLogger(__name__)


def _guess_media_type(path: str):
    """Returns ('video'|'audio'|'document', mime)"""
    mime, _ = mimetypes.guess_type(path)
    if mime:
        if mime.startswith("video"):
            return "video", mime
        if mime.startswith("audio"):
            return "audio", mime
    return "document", mime or "application/octet-stream"


async def _resolve_thumb(bot: Client, thumb) -> str | None:
    """
    Pyrogram's thumb= must be a LOCAL file path.
    If `thumb` is a Telegram file_id (not a local path), download it first.
    Returns a local path or None.
    """
    if not thumb:
        return None

    # Already a valid local file — use as-is
    if os.path.isfile(str(thumb)):
        return thumb

    # Must be a file_id — download to a temp jpeg
    try:
        tmp = tempfile.mktemp(suffix=".jpg")
        downloaded = await bot.download_media(thumb, file_name=tmp)
        return downloaded
    except Exception as e:
        log.warning(f"Could not resolve thumbnail: {e}")
        return None


async def upload_file(
    bot: Client,
    chat_id: int,
    file_path: str,
    caption: str = "",
    thumb=None,
    as_document: bool = False,
    spoiler: bool = False,
    status_msg=None,
    user_name=None,   # ← accepted but intentionally unused (caller compat)
    user_id=None,     # ← accepted but intentionally unused (caller compat)
    **kwargs,         # ← absorbs any other unexpected keyword arguments
) -> None:
    """Upload a single file, choosing the best available client."""
    size   = os.path.getsize(file_path)
    TWO_GB = 2 * 1024 * 1024 * 1024

    # Use user client for files >2 GB if session string was provided
    client: Client = bot
    if size > TWO_GB and temp.U_CLIENT is not None:
        client = temp.U_CLIENT

    # ── Resolve thumbnail to a local path ────────────────────────────────────
    local_thumb = await _resolve_thumb(bot, thumb)
    # Track if we need to clean up a downloaded temp file after upload
    thumb_is_tmp = (
        local_thumb is not None
        and thumb is not None
        and not os.path.isfile(str(thumb))
    )

    media_type, _ = _guess_media_type(file_path)
    cb = make_progress(status_msg, "Uploading") if status_msg else None

    kwargs = dict(
        chat_id=chat_id,
        caption=caption,
        thumb=local_thumb,   # always a local path or None
        progress=cb,
    )

    try:
        if as_document or media_type == "document":
            await client.send_document(document=file_path, **kwargs)
        elif media_type == "video":
            await client.send_video(
                video=file_path,
                supports_streaming=True,
                has_spoiler=spoiler,
                **kwargs
            )
        elif media_type == "audio":
            await client.send_audio(audio=file_path, **kwargs)
        else:
            await client.send_document(document=file_path, **kwargs)
    finally:
        # Delete the temp thumbnail we downloaded (if any)
        if thumb_is_tmp and local_thumb and os.path.exists(local_thumb):
            try:
                os.remove(local_thumb)
            except Exception:
                pass
