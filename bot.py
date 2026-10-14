from pyrogram import Client
from pyrogram.enums import ParseMode
from config import API_ID, API_HASH, BOT_TOKEN


class Bot(Client):
    def __init__(self):
        super().__init__(
            "linkbot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="plugins"),
            workers=50,
            parse_mode=ParseMode.HTML,
        )

    async def start(self):
        await super().start()
        print(f"Bot started as @{self.me.username}")

    async def stop(self, *args):
        await super().stop()
        print("Bot stopped")


if __name__ == "__main__":
    Bot().run()
