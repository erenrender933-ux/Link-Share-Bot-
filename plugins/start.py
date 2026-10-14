import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import db
from helpers import (
    get_missing, join_markup, get_channel_link, link_expired, decode_id, expiry_text,
    INDEX_TEXT, JOIN_TEXT, letters_markup,
)
from config import INDEX_LINK_EXPIRE


@Client.on_message(filters.command("start") & filters.private)
async def start(client, message):
    uid = message.from_user.id
    await db.add_user(uid)
    payload = message.command[1] if len(message.command) > 1 else None

    # decode shared link payload
    cid, request = None, False
    if payload:
        request = payload.startswith("req_")
        try:
            cid = decode_id(payload[4:] if request else payload)
        except Exception:
            return await message.reply("❌ Invalid link.")

    # force-sub gate (the target channel itself is never required)
    missing = await get_missing(client, uid, exclude=cid)
    if missing:
        retry = f"https://t.me/{client.me.username}?start={payload}" if payload else None
        return await message.reply(JOIN_TEXT, reply_markup=join_markup(missing, retry))

    # normal /start
    if not payload:
        return await message.reply(
            f"<b>Hello {message.from_user.mention}!</b>\n\n"
            "Browse all anime channels from the index below.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("📚 Index", callback_data="idx_home")]]
            ),
        )

    # shared channel link
    if not await db.get_channel(cid):
        return await message.reply("❌ Invalid or removed link.")
    try:
        url, temp = await get_channel_link(client, cid, request)
    except Exception:
        return await message.reply("❌ Could not create the link. Please tell the admin.")

    text = "<b><blockquote>⚡ ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ!.</blockquite>/n/n<blockquote>⏳ ᴄʟɪᴄᴋ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ.</blockquote></b>"
    if temp:
        text += "\n\n" + expiry_text()
    label = "• ɢɪᴠᴇ ʀᴇǫ 🔗 •" if request else "• ᴊᴏɪɴ 🔗 •"
    m = await message.reply(
        text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(label, url=url)]])
    )
    if temp:
        retry_url = f"https://t.me/{client.me.username}?start={payload}"
        asyncio.create_task(link_expired(client, m.chat.id, m.id, INDEX_LINK_EXPIRE, retry_url))


@Client.on_callback_query(filters.regex("^recheck$"))
async def recheck(client, q):
    missing = await get_missing(client, q.from_user.id)
    if missing:
        return await q.answer("You have not joined all channels yet!", show_alert=True)
    await q.message.edit_text(INDEX_TEXT, reply_markup=letters_markup())


@Client.on_callback_query(filters.regex("^close$"))
async def close_cb(client, q):
    try:
        await q.message.delete()
    except Exception:
        pass
