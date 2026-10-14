from pyrogram import Client, filters
from config import ADMINS, MAX_FSUB
from database import db

admin = filters.user(ADMINS) & filters.private


def link_id(link: str) -> str:
    return (link or "").rstrip("/").split("/")[-1]


@Client.on_message(filters.command("addfsub") & admin)
async def addfsub(client, message):
    # /addfsub -100xxxxxxxxxx        -> normal join link
    # /addfsub -100xxxxxxxxxx req    -> join request link
    if len(message.command) < 2:
        return await message.reply(
            "Usage:\n<code>/addfsub -100xxxxxxxxxx</code>\n<code>/addfsub -100xxxxxxxxxx req</code>"
        )
    cid = int(message.command[1])
    if not await db.get_fsub_one(cid) and len(await db.get_fsub()) >= MAX_FSUB:
        return await message.reply(f"❌ Maximum {MAX_FSUB} channels allowed.")
    req = len(message.command) > 2 and message.command[2].lower().startswith("req")
    try:
        chat = await client.get_chat(cid)
        link = await client.create_chat_invite_link(cid, creates_join_request=req)
    except Exception as e:
        return await message.reply(f"❌ Error: <code>{e}</code>\nMake the bot admin in that channel.")
    await db.add_fsub(cid, chat.title, link.invite_link, req)
    await message.reply(f"✅ Added: <b>{chat.title}</b> ({'request' if req else 'normal'})")


@Client.on_message(filters.command("delfsub") & admin)
async def delfsub(client, message):
    if len(message.command) < 2:
        return await message.reply("Usage: <code>/delfsub -100xxxxxxxxxx</code>")
    await db.del_fsub(int(message.command[1]))
    await message.reply("✅ Removed.")


@Client.on_message(filters.command("fsublist") & admin)
async def fsublist(client, message):
    items = await db.get_fsub()
    if not items:
        return await message.reply("No force-sub channels.")
    lines = []
    for n, c in enumerate(items, 1):
        goal = f" | goal {c['count']}/{c['goal']}" if c.get("goal") else ""
        lines.append(
            f"{n}. {c['title']} — <code>{c['_id']}</code> "
            f"({'request' if c['request'] else 'normal'}){goal}"
        )
    await message.reply("<b>Force-sub channels:</b>\n\n" + "\n".join(lines))


# ---------------- Goal ----------------
@Client.on_message(filters.command("setgoal") & admin)
async def setgoal(client, message):
    # /setgoal -100xxxxxxxxxx 1000   -> one request link, count join requests until goal
    # /setgoal -100xxxxxxxxxx 0      -> remove goal
    if len(message.command) < 3:
        return await message.reply(
            "Usage:\n<code>/setgoal -100xxxxxxxxxx 1000</code>\n"
            "<code>/setgoal -100xxxxxxxxxx 0</code> (remove goal)"
        )
    try:
        cid = int(message.command[1])
        goal = int(message.command[2])
    except ValueError:
        return await message.reply("❌ Invalid values.")
    if not await db.get_fsub_one(cid):
        return await message.reply("❌ Add this channel first with /addfsub")
    if goal <= 0:
        await db.clear_goal(cid)
        return await message.reply("✅ Goal removed.")
    try:
        link = await client.create_chat_invite_link(
            cid, name="goal-link", creates_join_request=True
        )
    except Exception as e:
        return await message.reply(f"❌ Error: <code>{e}</code>")
    await db.set_goal(cid, goal, link.invite_link)
    await message.reply(
        f"✅ Goal set: <b>{goal}</b> join requests\n\n"
        f"Single request link:\n{link.invite_link}\n\n"
        "You will be notified when the goal is complete. Check progress with /goals",
        disable_web_page_preview=True,
    )


@Client.on_message(filters.command("goals") & admin)
async def goals(client, message):
    items = [c for c in await db.get_fsub() if c.get("goal", 0) > 0]
    if not items:
        return await message.reply("No goals set. Use /setgoal")
    out = []
    for c in items:
        pct = min(100, int(c["count"] * 100 / c["goal"]))
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        status = "✅ Completed" if c["count"] >= c["goal"] else "⏳ In progress"
        out.append(
            f"<b>{c['title']}</b>\n{bar} {pct}%\n"
            f"{c['count']}/{c['goal']} requests — {status}\n{c['link']}"
        )
    await message.reply("\n\n".join(out), disable_web_page_preview=True)


# ---------------- Join request tracking ----------------
@Client.on_chat_join_request()
async def on_request(client, req):
    cid = req.chat.id
    ch = await db.get_fsub_one(cid)
    if not ch:
        return
    uid = req.from_user.id
    await db.add_request(uid, cid)  # lets the user pass force-sub

    if ch.get("goal", 0) <= 0:
        return
    used = req.invite_link.invite_link if req.invite_link else ""
    if link_id(used) != link_id(ch["link"]):
        return  # request did not come from the goal link
    if not await db.add_goal_user(uid, cid):
        return
    doc = await db.inc_goal(cid)
    if doc["count"] >= doc["goal"] and await db.mark_notified(cid):
        for admin_id in ADMINS:
            try:
                await client.send_message(
                    admin_id,
                    f"🎯 <b>Goal completed!</b>\n\n"
                    f"Channel: <b>{doc['title']}</b>\n"
                    f"Requests: {doc['count']}/{doc['goal']}",
                )
            except Exception:
                pass
