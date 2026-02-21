import pytz
import datetime
from script import script
from config import Config
from utils import get_seconds, temp
from database import db
import asyncio
from pyrogram import Client, filters
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong
from pyrogram.types import *

ADMINS = Config.ADMINS
PREMIUM_LOGS = Config.PREMIUM_LOGS
STAR_PREMIUM_PLANS = Config.STAR_PREMIUM_PLANS
SUBSCRIPTION = "https://i.ibb.co/gMrpRQWP/photo-2025-07-09-05-21-32-7524948058832896004.jpg"


@Client.on_message(filters.command("remove_premium") & filters.user(ADMINS))
async def remove_premium(client, message):
    if len(message.command) == 2:
        user_id = int(message.command[1])
        user = await client.get_users(user_id)
        if await db.remove_premium_access(user_id):
            await message.reply_text("ᴜꜱᴇʀ ʀᴇᴍᴏᴠᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ !")
            await client.send_message(
                chat_id=user_id,
                text=script.PREMIUM_END_TEXT.format(user.mention)
            )
        else:
            await message.reply_text("ᴜɴᴀʙʟᴇ ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴜꜱᴇᴅ !\nᴀʀᴇ ʏᴏᴜ ꜱᴜʀᴇ, ɪᴛ ᴡᴀꜱ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ɪᴅ ?")
    else:
        await message.reply_text("ᴜꜱᴀɢᴇ : /remove_premium user_id")


@Client.on_message(filters.command("myplan"))
async def myplan(client, message):
    try:
        user = message.from_user.mention
        user_id = message.from_user.id
        data = await db.get_user(user_id)

        if data and data.get("expiry_time"):
            expiry = data.get("expiry_time")
            expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
            expiry_str_in_ist = expiry_ist.strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")

            current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
            time_left = expiry_ist - current_time
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_left_str = f"{days} ᴅᴀʏꜱ, {hours} ʜᴏᴜʀꜱ, {minutes} ᴍɪɴᴜᴛᴇꜱ"

            caption = (
                f"⚜️ <b>ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ᴅᴀᴛᴀ :</b>\n\n"
                f"👤 <b>ᴜꜱᴇʀ :</b> {user}\n"
                f"⚡ <b>ᴜꜱᴇʀ ɪᴅ :</b> <code>{user_id}</code>\n"
                f"⏰ <b>ᴛɪᴍᴇ ʟᴇꜰᴛ :</b> {time_left_str}\n"
                f"⌛️ <b>ᴇxᴘɪʀʏ ᴅᴀᴛᴇ :</b> {expiry_str_in_ist}"
            )

            await message.reply_photo(
                photo=SUBSCRIPTION,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔥 ᴇxᴛᴇɴᴅ ᴘʟᴀɴ", callback_data="premium_info")]]
                )
            )
        else:
            await message.reply_photo(
                photo=SUBSCRIPTION,
                caption=(
                    f"<b>ʜᴇʏ {user},\n\n"
                    f"ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀɴ ᴀᴄᴛɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴ.\n"
                    f"ʙᴜʏ ᴏᴜʀ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ᴛᴏ ᴇɴᴊᴏʏ ᴘʀᴇᴍɪᴜᴍ ʙᴇɴᴇꜰɪᴛꜱ.</b>"
                ),
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("💎 ᴄʜᴇᴄᴋᴏᴜᴛ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴꜱ", callback_data='premium_info')]]
                )
            )
    except Exception as e:
        print(e)


@Client.on_message(filters.command("get_premium") & filters.user(ADMINS))
async def get_premium(client, message):
    if len(message.command) == 2:
        user_id = int(message.command[1])
        user = await client.get_users(user_id)
        data = await db.get_user(user_id)
        if data and data.get("expiry_time"):
            expiry = data.get("expiry_time")
            expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
            expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime(
                "%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")
            current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
            time_left = expiry_ist - current_time
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_left_str = f"{days} days, {hours} hours, {minutes} minutes"
            await message.reply_text(
                f"⚜️ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ᴅᴀᴛᴀ :\n\n"
                f"👤 ᴜꜱᴇʀ : {user.mention}\n"
                f"⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n"
                f"⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n"
                f"⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}"
            )
        else:
            await message.reply_text("ɴᴏ ᴀɴʏ ᴘʀᴇᴍɪᴜᴍ ᴅᴀᴛᴀ ᴏꜰ ᴛʜᴇ ᴡᴀꜱ ꜰᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀꜱᴇ !")
    else:
        await message.reply_text("ᴜꜱᴀɢᴇ : /get_premium user_id")


@Client.on_message(filters.command("add_premium") & filters.user(ADMINS))
async def give_premium_cmd_handler(client, message):
    if len(message.command) == 4:
        time_zone = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        current_time = time_zone.strftime("%d-%m-%Y\n⏱️ ᴊᴏɪɴɪɴɢ ᴛɪᴍᴇ : %I:%M:%S %p")
        user_id = int(message.command[1])
        user = await client.get_users(user_id)
        time = message.command[2] + " " + message.command[3]
        seconds = await get_seconds(time)
        if seconds > 0:
            expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
            user_data = {"id": user_id, "expiry_time": expiry_time}
            await db.update_user(user_data)
            data = await db.get_user(user_id)
            expiry = data.get("expiry_time")
            expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime(
                "%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")
            await message.reply_text(
                f"ᴘʀᴇᴍɪᴜᴍ ᴀᴅᴅᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ✅\n\n"
                f"👤 ᴜꜱᴇʀ : {user.mention}\n"
                f"⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n"
                f"⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ : <code>{time}</code>\n\n"
                f"⏳ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ : {current_time}\n\n"
                f"⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}",
                disable_web_page_preview=True
            )
            await client.send_message(
                chat_id=user_id,
                text=(
                    f"👋 ʜᴇʏ {user.mention},\n"
                    f"ᴛʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ᴘᴜʀᴄʜᴀꜱɪɴɢ ᴘʀᴇᴍɪᴜᴍ.\n"
                    f"ᴇɴᴊᴏʏ !! ✨🎉\n\n"
                    f"⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ : <code>{time}</code>\n"
                    f"⏳ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ : {current_time}\n\n"
                    f"⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}"
                ),
                disable_web_page_preview=True
            )
            if PREMIUM_LOGS:
                await client.send_message(
                    PREMIUM_LOGS,
                    text=(
                        f"#Added_Premium\n\n"
                        f"👤 ᴜꜱᴇʀ : {user.mention}\n"
                        f"⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n"
                        f"⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ : <code>{time}</code>\n\n"
                        f"⏳ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ : {current_time}\n\n"
                        f"⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}"
                    ),
                    disable_web_page_preview=True
                )
        else:
            await message.reply_text(
                "❌ ɪɴᴠᴀʟɪᴅ ᴛɪᴍᴇ ꜰᴏʀᴍᴀᴛ ❗\n"
                "🕒 ᴘʟᴇᴀsᴇ ᴜsᴇ: <code>1 day</code>, <code>1 hour</code>, "
                "<code>1 min</code>, <code>1 month</code>, or <code>1 year</code>"
            )
    else:
        await message.reply_text(
            "📌 ᴜsᴀɢᴇ: <code>/add_premium user_id time</code>\n"
            "📅 ᴇxᴀᴍᴘʟᴇ: <code>/add_premium 123456 1 month</code>\n"
            "🧭 ᴀᴄᴄᴇᴘᴛᴇᴅ ꜰᴏʀᴍᴀᴛs: <code>1 day</code>, <code>1 hour</code>, "
            "<code>1 min</code>, <code>1 month</code>, <code>1 year</code>"
        )


@Client.on_message(filters.command("premium_users") & filters.user(ADMINS))
async def premium_user(client, message):
    aa = await message.reply_text("<i>ꜰᴇᴛᴄʜɪɴɢ...</i>")
    new = " ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀꜱ ʟɪꜱᴛ :\n\n"
    user_count = 1
    users = db.users.find({})
    async for user in users:
        data = await db.get_user(user['id'])
        if data and data.get("expiry_time"):
            expiry = data.get("expiry_time")
            expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
            expiry_str_in_ist = expiry_ist.strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")
            current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
            time_left = expiry_ist - current_time
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_left_str = f"{days} days, {hours} hours, {minutes} minutes"
            new += (
                f"{user_count}. {(await client.get_users(user['id'])).mention}\n"
                f"👤 ᴜꜱᴇʀ ɪᴅ : {user['id']}\n"
                f"⏳ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}\n"
                f"⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n"
            )
            user_count += 1
    try:
        await aa.edit_text(new)
    except MessageTooLong:
        with open('usersplan.txt', 'w+') as f:
            f.write(new)
        await message.reply_document('usersplan.txt', caption="Paid Users:")


@Client.on_message(filters.command("plan"))
async def plan(client, message):
    user_id = message.from_user.id
    users = message.from_user.mention
    btn = [[
        InlineKeyboardButton('• ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ •', callback_data='buy_info'),
    ], [
        InlineKeyboardButton('🚫 ᴄʟᴏꜱᴇ 🚫', callback_data='close_data')
    ]]
    msg = await message.reply_photo(
        photo="https://graph.org/file/86da2027469565b5873d6.jpg",
        caption=script.BPREMIUM_TXT,
        reply_markup=InlineKeyboardMarkup(btn)
    )
    if PREMIUM_LOGS:
        await client.send_message(
            PREMIUM_LOGS,
            f"<b><u>🚫 ᴛʜɪs ᴜsᴇʀs ᴛʀʏ ᴛᴏ ᴄʜᴇᴄᴋ /plan</u>\n\n"
            f"- ɪᴅ - `{user_id}`\n- ɴᴀᴍᴇ - {users}</b>"
        )
    await asyncio.sleep(300)
    try:
        await msg.delete()
        await message.delete()
    except Exception:
        pass


# ── Premium info callback ─────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^premium_info$"))
async def premium_info_cb(client, query):
    plans_text = "\n".join(
        [f"⭐ <b>{stars} Stars</b> → {dur}" for stars, dur in STAR_PREMIUM_PLANS.items()]
    )
    buttons = [
        [InlineKeyboardButton(f"⭐ {stars} Stars — {dur}", callback_data=f"buy_{stars}")]
        for stars, dur in STAR_PREMIUM_PLANS.items()
    ]
    buttons.append([InlineKeyboardButton("🔙 Close", callback_data="close_data")])
    await query.message.reply_text(
        f"💎 <b>Premium Plans</b>\n\n{plans_text}\n\n"
        f"<i>Pay with Telegram Stars directly!</i>",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await query.answer()


# ── Telegram Star Payment ─────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^buy_\d+$"))
async def premium_button(client, callback_query):
    try:
        amount = int(callback_query.data.split("_")[1])
        if amount in STAR_PREMIUM_PLANS:
            buttons = [[InlineKeyboardButton("ᴄᴀɴᴄᴇʟ 🚫", callback_data="close_data")]]
            await client.send_invoice(
                chat_id=callback_query.message.chat.id,
                title="Premium Subscription",
                description=f"Pay {amount} Star And Get Premium For {STAR_PREMIUM_PLANS[amount]}",
                payload=f"renamepremium_{amount}",
                currency="XTR",
                prices=[LabeledPrice(label="Premium Subscription", amount=amount)],
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            await callback_query.answer()
        else:
            await callback_query.answer("⚠️ Invalid Premium Package.", show_alert=True)
    except Exception as e:
        print(f"Error In buy_ - {e}")


def successful_payment_filter(_, __, message):
    try:
        return hasattr(message, 'successful_payment') and message.successful_payment is not None
    except AttributeError:
        return False


successful_payment = filters.create(successful_payment_filter)


@Client.on_message(successful_payment & filters.private)
async def successful_premium_payment(client, message):
    try:
        payload = message.successful_payment.invoice_payload
        amount  = int(message.successful_payment.total_amount)
        user_id = message.from_user.id
        time_zone = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        current_time = time_zone.strftime("%d-%m-%Y | %I:%M:%S %p")

        if payload.startswith("renamepremium_"):
            amount = int(payload.split("_")[1])

        if amount in STAR_PREMIUM_PLANS:
            time = STAR_PREMIUM_PLANS[amount]
            seconds = await get_seconds(time)
            if seconds > 0:
                expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
                await db.update_user({"id": user_id, "expiry_time": expiry_time})
                data = await db.get_user(user_id)
                expiry = data.get("expiry_time")
                expiry_str = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime(
                    "%d-%m-%Y | %I:%M:%S %p")
                await message.reply(
                    f"Thank you for purchasing Premium ✅\n\n"
                    f"Subscription: {time}\nExpires: {expiry_str}",
                    disable_web_page_preview=True
                )
                if PREMIUM_LOGS:
                    await client.send_message(
                        PREMIUM_LOGS,
                        f"#Purchase_Premium_With_Star\n\n"
                        f"👤 User - {message.from_user.mention}\n"
                        f"⚡ ID - <code>{user_id}</code>\n"
                        f"⭐ Stars - {amount}\n"
                        f"⏰ Plan - {time}\n"
                        f"⌛ Expiry - {expiry_str}",
                        disable_web_page_preview=True
                    )
    except Exception as e:
        print(f"Error Processing Payment: {e}")
        await message.reply("✅ Thank You For Your Payment! (Error logging details)")
