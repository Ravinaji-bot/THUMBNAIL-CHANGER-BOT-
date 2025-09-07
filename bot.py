# bot.py
import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv
from db import set_thumb, get_thumb, del_thumb
from thumbs import ensure_dir, image_to_jpeg_thumb, extract_video_frame_as_thumb

load_dotenv()

API_ID = int(os.getenv("API_ID", "24196359"))
API_HASH = os.getenv("API_HASH", "20a1b32381ed174799e8af8def3e176b")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")

ensure_dir(DOWNLOAD_DIR)
ensure_dir(os.path.join(DOWNLOAD_DIR, "thumbs"))

app = Client("thumb_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workdir=DOWNLOAD_DIR)

# ---- Commands ----
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(c: Client, m: Message):
    await m.reply_text(
        "👋 Hi! I'm Thumbnail Changer Bot.\n\n"
        "Commands:\n"
        "/set_thumb - send an image or reply to an image to save as your thumbnail\n"
        "/show_thumb - show your saved thumbnail\n"
        "/del_thumb - delete saved thumbnail\n\n"
        "Send a video/document and I'll re-upload it with your saved thumbnail."
    )

# Save uploaded photo as user's thumbnail
@app.on_message(filters.command("set_thumb") & filters.private)
async def set_thumb_cmd(c: Client, m: Message):
    # Expect user to reply to an image or send an image right after command
    if m.reply_to_message and (m.reply_to_message.photo or m.reply_to_message.document):
        src = m.reply_to_message
    else:
        # ask user to send an image (but per instruction we won't wait; attempt best-effort)
        await m.reply_text("Please reply to the image you want to set as thumbnail.")
        return

    user_id = m.from_user.id
    file = None
    if src.photo:
        file = await src.photo.download(file_name=f"thumbs/{user_id}_orig.jpg")
    elif src.document:
        file = await src.document.download(file_name=f"thumbs/{user_id}_orig")
    else:
        await m.reply_text("Unsupported file. Send a photo or image document.")
        return

    # Convert/resize to a JPEG thumb
    thumb_path = f"thumbs/{user_id}_thumb.jpg"
    try:
        image_to_jpeg_thumb(file, thumb_path)
    except Exception as e:
        await m.reply_text(f"Failed to process thumbnail: {e}")
        return

    # Upload the thumb as a file to Telegram so we can reuse its file_id (optional optimization)
    # Simpler: store as local file and use when sending; but storing file_id avoids reupload.
    # We'll upload and store file_id as a document in the DB by sending to private chat (bot's own storage)
    uploaded = await c.send_photo(chat_id=user_id, photo=thumb_path, caption="✅ Thumb saved (temporary upload).")
    # get file_id to reuse
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

# When user sends a media (video/document), re-upload with their saved thumbnail if present
@app.on_message(filters.private & (filters.video | filters.document))
async def media_handler(c: Client, m: Message):
    user_id = m.from_user.id
    doc = get_thumb(user_id)
    if not doc:
        # no saved thumb, give simple echo
        await m.reply_text("You don't have a saved thumbnail. Use /set_thumb to save one, then resend the file.")
        return

    # Download the incoming file (video or doc)
    media = m.video or m.document
    fname = os.path.join(DOWNLOAD_DIR, f"{user_id}_upload_{media.file_unique_id}")
    path = await media.download(file_name=fname)

    # If the saved thumb is stored as file_id (we used send_photo earlier), download it locally
    thumb_local = os.path.join(DOWNLOAD_DIR, "thumbs", f"{user_id}_for_send.jpg")
    try:
        # download the saved thumb file_id into thumb_local
        await c.download_media(doc["file_id"], file_name=thumb_local)
    except Exception:
        # as fallback, try to use previously stored filename under thumbs/
        fallback = os.path.join("thumbs", f"{user_id}_thumb.jpg")
        if os.path.exists(fallback):
            thumb_local = fallback
        else:
            thumb_local = None

    # If the media is video, use send_video with thumb parameter
    try:
        if m.video:
            await c.send_chat_action(m.chat.id, "upload_video")
            await c.send_video(
                chat_id=m.chat.id,
                video=path,
                thumb=thumb_local if thumb_local else None,
                caption=f"Here you go — reuploaded with your thumbnail (user {user_id})"
            )
        else:
            # document: Telegram supports document thumb for certain types; use send_document thumb param
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
        # cleanup downloaded file
        try:
            os.remove(path)
        except:
            pass

if __name__ == "__main__":
    print("Starting Thumbnail Changer Bot...")
    app.run()
