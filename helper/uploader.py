"""
Smart uploader: uses user-session client for files >2 GB, bot client otherwise.
"""
import os
import mimetypes
from pyrogram import Client
from helper.progress import make_progress
from utils import get_readable_file_size, temp


def _guess_media_type(path: str):
    """Returns ('video'|'audio'|'document', mime)"""
    mime, _ = mimetypes.guess_type(path)
    if mime:
        if mime.startswith("video"):
            return "video", mime
        if mime.startswith("audio"):
            return "audio", mime
    return "document", mime or "application/octet-stream"


async def upload_file(
    bot: Client,
    chat_id: int,
    file_path: str,
    caption: str = "",
    thumb: str = None,
    as_document: bool = False,
    spoiler: bool = False,
    status_msg=None,
) -> None:
    """Upload a single file, choosing the best available client."""
    size = os.path.getsize(file_path)
    TWO_GB = 2 * 1024 * 1024 * 1024

    # Choose client: user client for large files if available
    client: Client = bot
    if size > TWO_GB and temp.U_CLIENT is not None:
        client = temp.U_CLIENT

    media_type, _ = _guess_media_type(file_path)
    cb = make_progress(status_msg, "Uploading") if status_msg else None

    kwargs = dict(
        chat_id=chat_id,
        caption=caption,
        thumb=thumb,
        progress=cb,
    )

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
