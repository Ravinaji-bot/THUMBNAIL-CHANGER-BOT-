# bot.py
import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv
from db import set_thumb, get_thumb, del_thumb, add_user, get_all_users
from thumbs import ensure_dir, image_to_jpeg_thumb, extract_video_frame_as_thumb
from db import set_thumb, get_thumb, del_thumb, add_user, get_all_users
load_dotenv()

API_ID = int(os.getenv("API_ID", "24196359"))
API_HASH = os.getenv("API_HASH", "20a1b32381ed174799e8af8def3e176b")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
ADMINS = [int(x) for x in os.getenv("ADMINS", "7404203924").split(",") if x.strip()]

ensure_dir(DOWNLOAD_DIR)
ensure_dir(os.path.join(DOWNLOAD_DIR, "thumbs"))

app = Client("thumb_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workdir=DOWNLOAD_DIR)

# ---- Commands ----
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(c: Client, m: Message):
    add_user(m.from_user.id)  # track user
    await m.reply_text(
        "👋 Hi! I'm Thumbnail Changer Bot.\n\n"
        "Commands:\n"
        "/set_thumb - send an image or reply to an image to save as your thumbnail\n"
        "/show_thumb - show your saved thumbnail\n"
        "/del_thumb - delete saved thumbnail\n"
        "/broadcast <message> - admin only\n\n"
        "Send a video or document and I'll re-upload it with your saved thumbnail."
    )

# Save uploaded photo as user's thumbnail
@app.on_message(filters.command("set_thumb") & filters.private)
async def set_thumb_cmd(c: Client, m: Message):
    user_id = m.from_user.id
    add_user(user_id)

    if m.reply_to_message and (m.reply_to_message.photo or m.reply_to_message.document):
        src = m.reply_to_message
    else:
        await m.reply_text("Please reply to the image you want to set as thumbnail.")
        return

    file = None
    if src.photo:
        file = await src.photo.download(file_name=f"thumbs/{user_id}_orig.jpg")
    elif src.document:
        file = await src.document.download(file_name=f"thumbs/{user_id}_orig")
    else:
        await m.reply_text("Unsupported file. Send a photo or image document.")
        return

    thumb_path = f"thumbs/{user_id}_thumb.jpg"
    try:
        image_to_jpeg_thumb(file, thumb_path)
    except Exception as e:
        await m.reply_text(f"Failed to process thumbnail: {e}")
        return

    uploaded = await c.send_photo(chat_id=user_id, photo=thumb_path, caption="✅ Thumb saved (temporary upload).")
    file_id = uploaded.photo.file_id
    set_thumb(user_id, file_id, os.path.basename(thumb_path), "image/jpeg")
    await m.reply_text("✅ Thumbnail saved! Now send a video or document and I'll attach it for you.\nUse /show_thumb or /del_thumb.")

# Show current thumb
@app.on_message(filters.command("show_thumb") & filters.private)
async def show_thumb_cmd(c: Client, m: Message):
    user_id = m.from_user.id
    doc = get_thumb(user_id)
    if not doc:
        await m.reply_text("You have no saved thumbnail. Use /set_thumb.")
        return
    await c.send_photo(chat_id=m.chat.id, photo=doc["file_id"], caption="Your saved thumbnail")

# Delete thumb
@app.on_message(filters.command("del_thumb") & filters.private)
async def del_thumb_cmd(c: Client, m: Message):
    user_id = m.from_user.id
    doc = get_thumb(user_id)
    if not doc:
        await m.reply_text("No thumbnail to delete.")
        return
    del_thumb(user_id)
    await m.reply_text("Deleted saved thumbnail ✅")

# Broadcast message (Admin only)
@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_cmd(c: Client, m: Message):
    if m.from_user.id not in ADMINS:
        await m.reply_text("❌ You are not authorized to use this command.")
        return

    args = m.text.split(None, 1)
    if len(args) < 2:
        await m.reply_text("Usage: /broadcast <message>")
        return

    message = args[1]
    users = get_all_users()
    sent = 0
    for uid in users:
        try:
            await c.send_message(uid, message)
            sent += 1
        except:
            continue
    await m.reply_text(f"✅ Broadcast sent to {sent} users.")

# Handle media with user's thumbnail
@app.on_message(filters.private & (filters.video | filters.document))
async def media_handler(c: Client, m: Message):
    user_id = m.from_user.id
    add_user(user_id)
    doc = get_thumb(user_id)
    if not doc:
        await m.reply_text("You don't have a saved thumbnail. Use /set_thumb to save one, then resend the file.")
        return

    media = m.video or m.document
    fname = os.path.join(DOWNLOAD_DIR, f"{user_id}_upload_{media.file_unique_id}")
    path = await media.download(file_name=fname)

    thumb_local = os.path.join(DOWNLOAD_DIR, "thumbs", f"{user_id}_for_send.jpg")
    try:
        await c.download_media(doc["file_id"], file_name=thumb_local)
    except Exception:
        fallback = os.path.join("thumbs", f"{user_id}_thumb.jpg")
        if os.path.exists(fallback):
            thumb_local = fallback
        else:
            thumb_local = None

    try:
        if m.video:
            await c.send_chat_action(m.chat.id, "upload_video")
            await c.send_video(
                chat_id=m.chat.id,
                video=path,
                thumb=thumb_local if thumb_local else None,
                caption=f"Here you go — reuploaded with your thumbnail"
            )
        else:
            await c.send_chat_action(m.chat.id, "upload_document")
            await c.send_document(
                chat_id=m.chat.id,
                document=path,
                thumb=thumb_local if thumb_local else None,
                caption="Document reuploaded with your thumbnail (if supported)."
            )
    except Exception as e:
        await m.reply_text(f"Failed to re-upload with thumbnail: {e}")
    finally:
        try:
            os.remove(path)
        except:
            pass

if __name__ == "__main__":
    print("Starting Thumbnail Changer Bot with Admin & Broadcast...")
    app.run()
