import base64
import string
from datetime import datetime, timedelta
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMINS, ADMIN_BYPASS, INDEX_LINK_EXPIRE
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


def encode_id(cid: int) -> str:
    return base64.urlsafe_b64encode(str(cid).encode()).decode().strip("=")


def decode_id(code: str) -> int:
    code += "=" * (-len(code) % 4)
    return int(base64.urlsafe_b64decode(code.encode()).decode())


def letters_markup():
    letters = ["#"] + list(string.ascii_uppercase)
    rows = [
        [InlineKeyboardButton(f"『{l}』", callback_data=f"idx|{l}|0") for l in letters[i : i + 5]]
        for i in range(0, len(letters), 5)
    ]
    rows.append([InlineKeyboardButton("• Close •", callback_data="close")])
    return InlineKeyboardMarkup(rows)


def join_markup(missing, retry_url=None):
    rows = []
    for ch in missing:
        label = ("• ʀᴇǫᴜᴇsᴛᴇᴅ ᴛᴏ ᴊᴏɪɴ •" if ch["request"] else "• ᴊᴏɪɴ •") + ch["title"]
        rows.append([InlineKeyboardButton(label, url=ch["link"])])
    if retry_url:
        rows.append([InlineKeyboardButton("ᴛʀʏ ᴀɢᴀɪɴ♻️", url=retry_url)])
    else:
        rows.append([InlineKeyboardButton("ᴛʀʏ ᴀɢᴀɪɴ♻️", callback_data="recheck")])
    return InlineKeyboardMarkup(rows)


async def get_missing(client, user_id, exclude=None):
    """Force-sub channels the user has not joined (or requested) yet"""
    if ADMIN_BYPASS and user_id in ADMINS:
        return []
    missing = []
    for ch in await db.get_fsub():
        cid = ch["_id"]
        if cid == exclude:
            continue
        if await db.has_request(user_id, cid):
            continue
        try:
            m = await client.get_chat_member(cid, user_id)
            if m.status in JOINED:
                continue
            if m.status == ChatMemberStatus.RESTRICTED and getattr(m, "is_member", False):
                continue
        except UserNotParticipant:
            pass
        except Exception as e:
            print(f"[FSUB] cannot check channel {cid}: {e}")
            continue  # bot has no access there, skip so users are not stuck
        missing.append(ch)
    return missing


async def get_channel_link(client, cid, request=True):
    """
    Returns (url, temporary).
    - Active /setgoal on this channel: always the ONE single goal link.
    - Otherwise: a fresh invite link that expires in INDEX_LINK_EXPIRE seconds.
    """
    ch = await db.get_fsub_one(cid)
    if ch and ch.get("goal", 0) > 0:
        return ch["link"], False
    link = await client.create_chat_invite_link(
        cid,
        expire_date=datetime.now() + timedelta(seconds=INDEX_LINK_EXPIRE),
        creates_join_request=request,
        member_limit=None if request else 1,
    )
    return link.invite_link, True


async def send_link_messages(client, chat_id, url, label):
    """Link message with button, then a separate warning message below it"""
    await client.send_message(
        chat_id,
        "⚡ <b>ʜᴇʀᴇ ɪs ʏᴏᴜʀ ʟɪɴᴋ!</b>\n\nᴄʟɪᴄᴋ ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(label, url=url)]]),
    )
    await client.send_message(
        chat_id,
        "⚠️ <b>ɪғ ᴛʜᴇ ʟɪɴᴋ ᴇxᴘɪʀᴇs, ᴛʀʏ ᴀɢᴀɪɴ ᴏʀ ᴄʟɪᴄᴋ ᴛʜᴇ ᴘᴏsᴛ ʟɪɴᴋ ᴛᴏ ɢᴇᴛ ᴀ ɴᴇᴡ ᴏɴᴇ.</b>",
    )
