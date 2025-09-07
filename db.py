# db.py
from pymongo import MongoClient
import os

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL not set in env")

client = MongoClient(MONGO_URL)
db = client.get_default_database()
thumbs = db.thumbs  # collection: { user_id: int, file_id: str, filename: str, mime: str }

def set_thumb(user_id: int, file_id: str, filename: str, mime: str):
    thumbs.update_one({"user_id": user_id},
                      {"$set": {"file_id": file_id, "filename": filename, "mime": mime}},
                      upsert=True)

def get_thumb(user_id: int):
    doc = thumbs.find_one({"user_id": user_id})
    return doc

def del_thumb(user_id: int):
    thumbs.delete_one({"user_id": user_id})
