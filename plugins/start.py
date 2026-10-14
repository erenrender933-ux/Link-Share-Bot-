from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import db
from helpers import get_missing, join_markup, INDEX_TEXT, JOIN_TEXT, letters_markup


@Client.on_message(filters.command("start") & filters.private)
async def start(client, message):
    uid = message.from_user.id
    await db.add_user(uid)

    missing = await get_missing(client, uid)
    if missing:
        return await message.reply(JOIN_TEXT, reply_markup=join_markup(missing))

    await message.reply(
        f"<b>Hello {message.from_user.mention}!</b>\n\n"
        "Browse all anime channels from the index below.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("📚 Index", callback_data="idx_home")]]
        ),
    )


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
