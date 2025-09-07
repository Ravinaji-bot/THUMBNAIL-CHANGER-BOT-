# thumbs.py
import os
from PIL import Image
import tempfile
import subprocess

# Telegram likes JPEG thumbs. Resize max 320x320 for video doc thumbs.
MAX_DIM = 320

def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

def image_to_jpeg_thumb(input_path: str, output_path: str, max_dim=MAX_DIM):
    """Open input image, convert to JPEG, resize preserving aspect ratio to <= max_dim."""
    with Image.open(input_path) as im:
        im = im.convert("RGB")
        w, h = im.size
        scale = min(max_dim / w, max_dim / h, 1)
        if scale < 1:
            im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        im.save(output_path, "JPEG", quality=85)
    return output_path

def extract_video_frame_as_thumb(video_path: str, output_path: str, timestamp="00:00:01"):
    """Use ffmpeg to extract a frame (default at 1s) then convert to jpeg thumb."""
    # ffmpeg must be installed on system
    tmp = output_path + ".frame.png"
    cmd = [
        "ffmpeg", "-y", "-ss", timestamp, "-i", video_path,
        "-vframes", "1", "-q:v", "2", tmp
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not os.path.exists(tmp):
        raise RuntimeError("ffmpeg failed to extract frame")
    image_to_jpeg_thumb(tmp, output_path)
    os.remove(tmp)
    return output_path
      
