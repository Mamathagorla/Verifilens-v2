"""Audio extraction using yt-dlp - runs locally on AMD AI PC"""

import os
import uuid
import asyncio
from pathlib import Path
from dotenv import load_dotenv

import subprocess
import tempfile

load_dotenv()

TEMP_DIR = os.getenv("TEMP_AUDIO_DIR", "./temp_audio")
MAX_DURATION = int(os.getenv("MAX_VIDEO_DURATION", 300))
Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)


def detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "youtube.com/shorts" in url_lower:
        return "youtube_shorts"
    elif "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "instagram.com" in url_lower:
        return "instagram"
    elif "tiktok.com" in url_lower:
        return "tiktok"
    return "unknown"


async def extract_audio(url: str) -> dict:
    """Download audio from video URL. Audio stays on device - never uploaded."""
    platform = detect_platform(url)
    file_id = str(uuid.uuid4())[:8]
    output_template = os.path.join(TEMP_DIR, f"audio_{file_id}.%(ext)s")

    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--max-filesize", "50m",
        "--output", output_template,
        "--no-warnings",
        "--quiet",
        url
    ]

    print(f"[AudioExtractor] Downloading from {platform}: {url[:60]}...")

#""""
    def run_ytdlp():
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise Exception(f"yt-dlp failed: {result.stderr.decode().strip()}")

    try:
        # run yt-dlp in a background thread instead of asyncio subprocess
        await asyncio.wait_for(asyncio.to_thread(run_ytdlp), timeout=120)

        actual_file = None
        for ext in ["mp3", "m4a", "webm", "opus", "wav"]:
            candidate = os.path.join(TEMP_DIR, f"audio_{file_id}.{ext}")
            if os.path.exists(candidate):
                actual_file = candidate
                break

        if not actual_file:
            raise Exception("Audio file not found after download")

        duration = await get_audio_duration(actual_file)
        if duration > MAX_DURATION:
            os.remove(actual_file)
            raise Exception(f"Video too long ({duration:.0f}s). Max: {MAX_DURATION}s")

        print(f"[AudioExtractor] ✅ Downloaded: {actual_file} ({duration:.1f}s)")
        return {
            "file_path": actual_file,
            "duration": duration,
            "platform": platform,
            "file_id": file_id,
        }

    except asyncio.TimeoutError:
        raise Exception("Download timed out after 2 minutes")
#""""


    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)

        if process.returncode != 0:
            raise Exception(f"yt-dlp failed: {stderr.decode().strip()}")

        actual_file = None
        for ext in ["mp3", "m4a", "webm", "opus", "wav"]:
            candidate = os.path.join(TEMP_DIR, f"audio_{file_id}.{ext}")
            if os.path.exists(candidate):
                actual_file = candidate
                break

        if not actual_file:
            raise Exception("Audio file not found after download")

        duration = await get_audio_duration(actual_file)
        if duration > MAX_DURATION:
            os.remove(actual_file)
            raise Exception(f"Video too long ({duration:.0f}s). Max: {MAX_DURATION}s")

        print(f"[AudioExtractor] ✅ Downloaded: {actual_file} ({duration:.1f}s)")
        return {"file_path": actual_file, "duration": duration, "platform": platform, "file_id": file_id}

    except asyncio.TimeoutError:
        raise Exception("Download timed out after 2 minutes")


async def get_audio_duration(file_path: str) -> float:
    def run_ffprobe():
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            return 0.0
        try:
            return float(result.stdout.decode().strip())
        except Exception:
            return 0.0

    return await asyncio.to_thread(run_ffprobe)

    '''"""
    try:
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        process = await asyncio.create_subprocess_exec(*cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await process.communicate()
        return float(stdout.decode().strip())
    except Exception:
        return 0.0
'''

def cleanup_audio(file_path: str):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            print(f"[AudioExtractor] 🗑️ Cleaned: {file_path}")
    except Exception as e:
        print(f"[AudioExtractor] Cleanup warning: {e}")
