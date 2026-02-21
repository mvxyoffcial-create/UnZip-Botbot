import datetime
import pytz
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config


class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db     = self.client[Config.DATABASE_NAME]
        self.users  = self.db["users"]
        self.chats  = self.db["chats"]

    # ──────────────────────────────────────────────────────────────────────────
    # USER helpers
    # ──────────────────────────────────────────────────────────────────────────
    async def add_user(self, user_id: int):
        user = await self.users.find_one({"id": user_id})
        if not user:
            await self.users.insert_one({
                "id":              user_id,
                "join_date":       datetime.datetime.utcnow(),
                "expiry_time":     None,
                "thumbnail":       None,
                "timezone":        "Asia/Kolkata",
                "spoiler":         False,
                "rename":          True,
                "as_document":     False,
                "screenshots":     True,
                "bot_updates":     True,
                "banned":          False,
            })

    async def get_user(self, user_id: int):
        return await self.users.find_one({"id": user_id})

    async def update_user(self, data: dict):
        uid = data.pop("id")
        await self.users.update_one({"id": uid}, {"$set": data}, upsert=True)
        data["id"] = uid

    async def get_all_users(self):
        return self.users.find({})

    async def total_users_count(self) -> int:
        return await self.users.count_documents({})

    async def get_banned_users(self):
        return self.users.find({"banned": True})

    async def ban_user(self, user_id: int):
        await self.users.update_one({"id": user_id}, {"$set": {"banned": True}}, upsert=True)

    async def unban_user(self, user_id: int):
        await self.users.update_one({"id": user_id}, {"$set": {"banned": False}})

    async def is_banned(self, user_id: int) -> bool:
        u = await self.get_user(user_id)
        return bool(u and u.get("banned"))

    # ──────────────────────────────────────────────────────────────────────────
    # PREMIUM helpers
    # ──────────────────────────────────────────────────────────────────────────
    async def is_premium(self, user_id: int) -> bool:
        u = await self.get_user(user_id)
        if not u:
            return False
        expiry = u.get("expiry_time")
        if expiry and expiry > datetime.datetime.utcnow():
            return True
        return False

    async def remove_premium_access(self, user_id: int) -> bool:
        u = await self.get_user(user_id)
        if u and u.get("expiry_time"):
            await self.users.update_one({"id": user_id}, {"$set": {"expiry_time": None}})
            return True
        return False

    # ──────────────────────────────────────────────────────────────────────────
    # SETTINGS helpers
    # ──────────────────────────────────────────────────────────────────────────
    async def get_setting(self, user_id: int, key: str):
        u = await self.get_user(user_id)
        return u.get(key) if u else None

    async def toggle_setting(self, user_id: int, key: str) -> bool:
        u = await self.get_user(user_id)
        current = u.get(key, False) if u else False
        new_val = not current
        await self.users.update_one({"id": user_id}, {"$set": {key: new_val}}, upsert=True)
        return new_val

    async def set_thumbnail(self, user_id: int, file_id: str):
        await self.users.update_one({"id": user_id}, {"$set": {"thumbnail": file_id}}, upsert=True)

    async def del_thumbnail(self, user_id: int):
        await self.users.update_one({"id": user_id}, {"$set": {"thumbnail": None}})

    async def set_timezone(self, user_id: int, tz: str):
        await self.users.update_one({"id": user_id}, {"$set": {"timezone": tz}}, upsert=True)

    # ──────────────────────────────────────────────────────────────────────────
    # CHAT helpers
    # ──────────────────────────────────────────────────────────────────────────
    async def add_chat(self, chat_id: int):
        chat = await self.chats.find_one({"id": chat_id})
        if not chat:
            await self.chats.insert_one({"id": chat_id, "join_date": datetime.datetime.utcnow()})

    async def get_all_chats(self):
        return self.chats.find({})

    async def total_chat_count(self) -> int:
        return await self.chats.count_documents({})


db = Database()
