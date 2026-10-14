from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMINS
from database import db

admin = filters.user(ADMINS) & filters.private


# /link -100xxxxxxxxxx [minutes]
# Creates a join-request link and sends a ready-to-forward share message
@Client.on_message(filters.command("link") & admin)
async def link_cmd(client, message):
    if len(message.command) < 2:
        return await message.reply(
            "Usage:\n<code>/link -100xxxxxxxxxx</code>\n"
            "<code>/link -100xxxxxxxxxx 10</code> (valid for 10 minutes)"
        )
    try:
        cid = int(message.command[1])
        minutes = int(message.command[2]) if len(message.command) > 2 else 5
        chat = await client.get_chat(cid)
        link = await client.create_chat_invite_link(
            cid,
            expire_date=datetime.now() + timedelta(minutes=minutes),
            creates_join_request=True,
        )
    except Exception as e:
        return await message.reply(f"❌ Error: <code>{e}</code>\nMake the bot admin in that channel.")

    await message.reply(
        f"<b>{chat.title}</b>\n\n"
        f"Your request link is ready!\nValid for {minutes} minutes.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(f"• Join {chat.title} •", url=link.invite_link)]]
        ),
    )


# /sharelinks
# Sends one message with a join button for every force-sub channel
@Client.on_message(filters.command("sharelinks") & admin)
async def sharelinks(client, message):
    items = await db.get_fsub()
    if not items:
        return await message.reply("No channels found. Add them with /addfsub first.")
    rows = [[InlineKeyboardButton(f"• {c['title']} •", url=c["link"])] for c in items]
    await message.reply(
        "<b>Join our channels 👇</b>",
        reply_markup=InlineKeyboardMarkup(rows),
    )
