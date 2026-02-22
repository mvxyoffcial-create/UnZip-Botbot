from pyrogram import Client, filters
from pyrogram.types import Message
from script import script


@Client.on_message(filters.command("info"))
async def info_cmd(client: Client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    if not target:
        return await message.reply_text("❌ No user found.")

    try:
        full = await client.get_users(target.id)
        dc   = full.dc_id or "N/A"
    except Exception:
        full = target
        dc   = "N/A"

    first = full.first_name or "—"
    last  = full.last_name  or "—"
    uname = full.username   or "—"
    uid   = full.id

    text = script.INFO_TXT.format(
        first=first, last=last, uid=uid, dc=dc, uname=uname
    )

    # Try to send profile photo with info caption
    try:
        photos = []
        async for photo in client.get_chat_photos(uid, limit=1):
            photos.append(photo)

        if photos:
            await message.reply_photo(
                photo=photos[0].file_id,
                caption=text,
            )
            return
    except Exception:
        pass

    # No profile photo — send as text
    await message.reply_text(text, disable_web_page_preview=True)
