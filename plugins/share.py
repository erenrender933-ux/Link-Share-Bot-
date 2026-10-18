from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMINS
from database import db
from helpers import encode_id

admin = filters.user(ADMINS) & filters.private


# /link -100xxxxxxxxxx   (or /addch)
# Registers the channel and gives permanent shareable bot links
@Client.on_message(filters.command(["link", "addch"]) & admin)
async def link_cmd(client, message):
    if len(message.command) < 2:
        return await message.reply("Usage: <code>/link -100xxxxxxxxxx</code>")
    try:
        cid = int(message.command[1])
        chat = await client.get_chat(cid)
    except Exception as e:
        return await message.reply(f"❌ Error: <code>{e}</code>\nMake the bot admin in that channel.")

    await db.add_channel(cid, chat.title)
    code = encode_id(cid)
    bot = client.me.username
    await message.reply(
        f"✅ <b>Chat {chat.title}</b> (<code>{cid}</code>) has been added successfully.\n\n"
        f"🔗 <b>Normal Link:</b> <code>https://t.me/{bot}?start={code}</code>\n"
        f"🔗 <b>Request Link:</b> <code>https://t.me/{bot}?start=req_{code}</code>\n\n"
        "These links never expire. A fresh invite link is created every time someone opens them.",
        disable_web_page_preview=True,
    )


@Client.on_message(filters.command("delch") & admin)
async def delch(client, message):
    if len(message.command) < 2:
        return await message.reply("Usage: <code>/delch -100xxxxxxxxxx</code>")
    await db.del_channel(int(message.command[1]))
    await message.reply("✅ Removed. Its shared links will stop working.")


# /sharelinks -> one message with join buttons for all force-sub channels
@Client.on_message(filters.command("sharelinks") & admin)
async def sharelinks(client, message):
    items = await db.get_fsub()
    if not items:
        return await message.reply("No channels found. Add them with /addfsub first.")
    rows = [[InlineKeyboardButton(f"• {c['title']} •", url=c["link"])] for c in items]
    await message.reply("<b>Join our channels 👇</b>", reply_markup=InlineKeyboardMarkup(rows))
