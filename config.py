import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMINS = [int(x) for x in os.environ.get("ADMINS", "").split()]
MONGO_URL = os.environ.get("MONGO_URL", "")
DB_NAME = os.environ.get("DB_NAME", "linkbot")

MAX_FSUB = 6
INDEX_LINK_EXPIRE = 300  # 5 minutes
