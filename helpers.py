import asyncio
import string
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMINS
from database import db

JOINED = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}

INDEX_TEXT = (
    "📚 <b>ANIME &amp; CHANNEL INDEX</b>\n\n"
    "<blockquote>Select a letter below to browse channels starting with that letter. "
    "Click any anime to get its 5-minute request link!</blockquote>"
)

JOIN_TEXT = (
    "<b>You must join our channel(s) first to use this bot.</b>\n"
    "Join using the buttons below, then press Try Again."
)


def letters_markup():
    letters = ["#"] + list(string.ascii_uppercase)
    rows = [
        [InlineKeyboardButton(f"『{l}』", callback_data=f"idx|{l}|0") for l in letters[i : i + 5]]
        for i in range(0, len(letters), 5)
    ]
    rows.append([InlineKeyboardButton("• Close •", callback_data="close")])
    return InlineKeyboardMarkup(rows)


def join_markup(missing):
    rows = []
    for ch in missing:
        label = ("Request to Join " if ch["request"] else "Join ") + ch["title"]
        rows.append([InlineKeyboardButton(label, url=ch["link"])])
    rows.append([InlineKeyboardButton("Try Again ♻️", callback_data="recheck")])
    return InlineKeyboardMarkup(rows)


async def get_missing(client, user_id):
    """Force-sub channels the user has not joined (or requested) yet"""
    if user_id in ADMINS:
        return []
    missing = []
    for ch in await db.get_fsub():
        cid = ch["_id"]
        if await db.has_request(user_id, cid):
            continue
        try:
            m = await client.get_chat_member(cid, user_id)
            if m.status in JOINED:
                continue
        except UserNotParticipant:
            pass
        except Exception:
            continue  # bot is not admin there, skip
        missing.append(ch)
    return missing


async def delete_later(client, chat_id, msg_id, delay):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, msg_id)
    except Exception:
        pass


async def link_expired(client, chat_id, msg_id, seconds):
    """Delete the link message after expiry and send an expired notice"""
    await asyncio.sleep(seconds)
    try:
        await client.delete_messages(chat_id, msg_id)
    except Exception:
        pass
    await client.send_message(
        chat_id,
        f"<b>⏰ This link expired in {seconds // 60} min.</b>\n\n"
        "If the link is expired, click the post again to create a new link for you.",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("📚 Open Index", callback_data="idx_home")],
                [InlineKeyboardButton("• Close •", callback_data="close")],
            ]
        ),
    )
