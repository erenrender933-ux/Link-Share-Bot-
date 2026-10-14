import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMINS, INDEX_LINK_EXPIRE
from database import db
from helpers import (
    get_missing, join_markup, get_channel_link, link_expired, expiry_text,
    INDEX_TEXT, JOIN_TEXT, letters_markup,
)

PAGE = 10
admin = filters.user(ADMINS) & filters.private


async def gate(client, q):
    if await get_missing(client, q.from_user.id):
        await q.answer("Join the required channels first. Send /start", show_alert=True)
        return False
    return True


@Client.on_message(filters.command("index") & filters.private)
async def index_cmd(client, message):
    missing = await get_missing(client, message.from_user.id)
    if missing:
        return await message.reply(JOIN_TEXT, reply_markup=join_markup(missing))
    await message.reply(INDEX_TEXT, reply_markup=letters_markup())


@Client.on_callback_query(filters.regex("^idx_home$"))
async def idx_home(client, q):
    if not await gate(client, q):
        return
    try:
        await q.message.edit_text(INDEX_TEXT, reply_markup=letters_markup())
    except Exception:
        pass
    await q.answer()


@Client.on_callback_query(filters.regex(r"^idx\|"))
async def idx_letter(client, q):
    if not await gate(client, q):
        return
    _, letter, page = q.data.split("|")
    page = int(page)
    total = await db.count_index(letter)
    if total == 0:
        return await q.answer(f"No channels under {letter}", show_alert=True)
    items = await db.get_index(letter, page * PAGE, PAGE)
    rows = [[InlineKeyboardButton(i["name"], callback_data=f"go|{i['_id']}")] for i in items]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ Prev", callback_data=f"idx|{letter}|{page - 1}"))
    if (page + 1) * PAGE < total:
        nav.append(InlineKeyboardButton("Next ▶", callback_data=f"idx|{letter}|{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append(
        [
            InlineKeyboardButton("⬅ Back", callback_data="idx_home"),
            InlineKeyboardButton("• Close •", callback_data="close"),
        ]
    )
    await q.message.edit_text(
        f"📚 <b>Channels starting with 『{letter}』</b>  ({total})",
        reply_markup=InlineKeyboardMarkup(rows),
    )


@Client.on_callback_query(filters.regex(r"^go\|"))
async def go_channel(client, q):
    if not await gate(client, q):
        return
    cid = int(q.data.split("|")[1])
    try:
        url, temp = await get_channel_link(client, cid, True)
    except Exception:
        return await q.answer("Could not create the link. Please tell the admin.", show_alert=True)
    await q.answer()
    text = "<b>Here is your link! Click below to proceed.</b>"
    if temp:
        text += "\n\n" + expiry_text()
    m = await q.message.reply(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("• Request to Join •", url=url)]]),
    )
    if temp:
        asyncio.create_task(link_expired(client, m.chat.id, m.id, INDEX_LINK_EXPIRE))


# ---------------- Admin: manage index ----------------
@Client.on_message(filters.command("addindex") & admin)
async def addindex(client, message):
    # /addindex -100xxxxxxxxxx [custom name]
    if len(message.command) < 2:
        return await message.reply("Usage: <code>/addindex -100xxxxxxxxxx [name]</code>")
    try:
        cid = int(message.command[1])
        name = " ".join(message.command[2:]) or (await client.get_chat(cid)).title
    except Exception as e:
        return await message.reply(f"❌ Error: <code>{e}</code>\nMake the bot admin in that channel.")
    await db.add_index(cid, name)
    await message.reply(f"✅ Added to index: <b>{name}</b>")


@Client.on_message(filters.command("delindex") & admin)
async def delindex(client, message):
    if len(message.command) < 2:
        return await message.reply("Usage: <code>/delindex -100xxxxxxxxxx</code>")
    await db.del_index(int(message.command[1]))
    await message.reply("✅ Removed from index.")


@Client.on_message(filters.command("indexlist") & admin)
async def indexlist(client, message):
    items = await db.all_index()
    if not items:
        return await message.reply("Index is empty.")
    txt = "\n".join(f"{n}. {i['name']} — <code>{i['_id']}</code>" for n, i in enumerate(items, 1))
    await message.reply(f"<b>Index ({len(items)}):</b>\n\n{txt[:3900]}")
