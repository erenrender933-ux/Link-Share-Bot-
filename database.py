import motor.motor_asyncio as motor
from pymongo import ReturnDocument
from config import MONGO_URL, DB_NAME


def letter_of(name: str) -> str:
    for ch in name:
        if ch.isalpha() and ch.isascii():
            return ch.upper()
        if ch.isdigit():
            return "#"
    return "#"


class Database:
    def __init__(self):
        self.db = motor.AsyncIOMotorClient(MONGO_URL)[DB_NAME]
        self.users = self.db.users
        self.fsub = self.db.fsub
        self.reqs = self.db.requests
        self.goal_users = self.db.goal_users
        self.index = self.db.index
        self.channels = self.db.channels

    # ---------- users ----------
    async def add_user(self, uid):
        await self.users.update_one({"_id": uid}, {"$set": {"active": True}}, upsert=True)

    async def all_users(self):
        return [u["_id"] async for u in self.users.find({})]

    async def total_users(self):
        return await self.users.count_documents({})

    # ---------- force sub ----------
    async def add_fsub(self, cid, title, link, request):
        await self.fsub.update_one(
            {"_id": cid},
            {
                "$set": {"title": title, "link": link, "request": request},
                "$setOnInsert": {"goal": 0, "count": 0, "notified": False},
            },
            upsert=True,
        )

    async def del_fsub(self, cid):
        await self.fsub.delete_one({"_id": cid})
        await self.goal_users.delete_many({"cid": cid})

    async def get_fsub(self):
        return [c async for c in self.fsub.find({})]

    async def get_fsub_one(self, cid):
        return await self.fsub.find_one({"_id": cid})

    # ---------- join requests (force sub bypass) ----------
    async def add_request(self, uid, cid):
        await self.reqs.update_one({"_id": f"{uid}:{cid}"}, {"$set": {"ok": 1}}, upsert=True)

    async def has_request(self, uid, cid):
        return await self.reqs.find_one({"_id": f"{uid}:{cid}"}) is not None

    # ---------- goal ----------
    async def set_goal(self, cid, goal, link):
        await self.goal_users.delete_many({"cid": cid})
        await self.fsub.update_one(
            {"_id": cid},
            {"$set": {"goal": goal, "count": 0, "notified": False, "link": link, "request": True}},
        )

    async def clear_goal(self, cid):
        await self.goal_users.delete_many({"cid": cid})
        await self.fsub.update_one(
            {"_id": cid}, {"$set": {"goal": 0, "count": 0, "notified": False}}
        )

    async def add_goal_user(self, uid, cid):
        """True only if this user is counted for the first time"""
        r = await self.goal_users.update_one(
            {"_id": f"{uid}:{cid}"}, {"$setOnInsert": {"cid": cid}}, upsert=True
        )
        return r.upserted_id is not None

    async def inc_goal(self, cid):
        return await self.fsub.find_one_and_update(
            {"_id": cid}, {"$inc": {"count": 1}}, return_document=ReturnDocument.AFTER
        )

    async def mark_notified(self, cid):
        r = await self.fsub.update_one(
            {"_id": cid, "notified": False}, {"$set": {"notified": True}}
        )
        return r.modified_count == 1
        
# ---------- share channels ----------
    async def add_channel(self, cid, title):
        await self.channels.update_one({"_id": cid}, {"$set": {"title": title}}, upsert=True)

    async def get_channel(self, cid):
        return await self.channels.find_one({"_id": cid})

    async def del_channel(self, cid):
        await self.channels.delete_one({"_id": cid})
        
    # ---------- index ----------
    async def add_index(self, cid, name):
        await self.index.update_one(
            {"_id": cid}, {"$set": {"name": name, "letter": letter_of(name)}}, upsert=True
        )

    async def del_index(self, cid):
        await self.index.delete_one({"_id": cid})

    async def count_index(self, letter):
        return await self.index.count_documents({"letter": letter})

    async def get_index(self, letter, skip, limit):
        cur = self.index.find({"letter": letter}).sort("name", 1).skip(skip).limit(limit)
        return [i async for i in cur]

    async def all_index(self):
        return [i async for i in self.index.find({}).sort("name", 1)]


db = Database()
