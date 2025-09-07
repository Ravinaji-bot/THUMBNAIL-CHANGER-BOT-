from pymongo import MongoClient
import os

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL not set in env")

client = MongoClient(MONGO_URL)
db = client.get_default_database()

# Collection for user thumbnails
thumbs = db.thumbs  # { user_id: int, file_id: str, filename: str, mime: str }

# Collection for users
users = db.users  # { user_id: int }

# Thumbnail functions
def set_thumb(user_id: int, file_id: str, filename: str, mime: str):
    thumbs.update_one({"user_id": user_id},
                      {"$set": {"file_id": file_id, "filename": filename, "mime": mime}},
                      upsert=True)

def get_thumb(user_id: int):
    return thumbs.find_one({"user_id": user_id})

def del_thumb(user_id: int):
    thumbs.delete_one({"user_id": user_id})

# User functions
def add_user(user_id: int):
    """Add a user if not already in DB."""
    if not users.find_one({"user_id": user_id}):
        users.insert_one({"user_id": user_id})

def get_all_users():
    """Return a list of all user IDs."""
    return [user["user_id"] for user in users.find()]
