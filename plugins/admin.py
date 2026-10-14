import asyncio
from pyrogram import Client, filters
from config import ADMINS
from database import db

admin = filters.user(ADMINS) & filters.private


@Client.on_message(filters.command("users") & admin)
async def users(client, message):
    await message.reply(f"👥 Total users: <b>{await db.total_users()}</b>")


@Client.on_message(filters.command("broadcast") & admin)
async def broadcast(client, message):
    if not message.reply_to_message:
        return await message.reply("Reply to a message with /broadcast")
    ok = fail = 0
    status = await message.reply("Broadcasting...")
    for uid in await db.all_users():
        try:
            await message.reply_to_message.copy(uid)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await status.edit(f"✅ Done\nSuccess: {ok}\nFailed: {fail}")
