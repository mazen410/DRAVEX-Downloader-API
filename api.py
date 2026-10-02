"""
=====================================================
   YourName Downloader API - All-in-One Scraper
   Owner: Your Name
   Version: 1.0.0
=====================================================
تشغيل:
    pip install fastapi uvicorn[standard] yt-dlp
    python api.py

ثم افتح:
    http://localhost:8000/docs
=====================================================
"""

import os
import uuid
from pathlib import Path
from typing import Optional, List
from datetime import datetime

import yt_dlp
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

# ═══════════════════════════════════════════════
# ⚙️ الإعدادات - عدّل هنا فقط
# ═══════════════════════════════════════════════
API_NAME    = "DRAVEX Downloader API"
API_OWNER   = "ELSORY"                      # ← ضع اسمك هنا
API_VERSION = "1.0.0"
API_KEY     = "sk-DRAVEX-666-a7x9k2mp4"      # ← غيّرها!
DOWNLOAD_DIR = Path("./downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════
# 📝 النماذج
# ═══════════════════════════════════════════════
class VideoInfoRequest(BaseModel):
    url: HttpUrl

class DownloadRequest(BaseModel):
    url: HttpUrl
    quality: str = "best"        # best / 1080p / 720p / 480p / 4k
    audio_only: bool = False
    playlist: bool = False

class DownloadResponse(BaseModel):
    status: str
    message: str
    task_id: Optional[str] = None
    title: Optional[str] = None
    filename: Optional[str] = None
    download_url: Optional[str] = None

# ═══════════════════════════════════════════════
# 🔐 التحقق من API Key
# ═══════════════════════════════════════════════
async def verify_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API Key غير صحيح")
    return x_api_key

# ═══════════════════════════════════════════════
# 🎬 محرّك التنزيل
# ═══════════════════════════════════════════════
def _base_opts() -> dict:
    return {
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "nocheckcertificate": True,
    }

def get_video_info(url: str) -> dict:
    with yt_dlp.YoutubeDL(_base_opts()) as ydl:
        return ydl.extract_info(url, download=False)

def download_video(url: str, quality: str, audio_only: bool, playlist: bool) -> dict:
    opts = _base_opts()
    opts["noplaylist"] = not playlist

    if audio_only:
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }]
    elif quality in ("720p", "1080p", "480p", "360p", "4k"):
        height = quality.replace("p", "").replace("k", "000")
        opts["format"] = (
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]/best"
        )
    else:
        opts["format"] = "bestvideo+bestaudio/best"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

        if "entries" in info:
            return {
                "title": info.get("title"),
                "count": len([e for e in info["entries"] if e]),
                "type": "playlist",
            }

        filename = Path(ydl.prepare_filename(info)).name
        return {
            "title": info.get("title"),
            "filename": filename,
            "type": "video",
        }

# ═══════════════════════════════════════════════
# 🚀 التطبيق
# ═══════════════════════════════════════════════
app = FastAPI(
    title=API_NAME,
    version=API_VERSION,
    description=f"API خاص بـ {API_OWNER} لتنزيل الفيديوهات",
    contact={"name": API_OWNER},
)

app.mount("/files", StaticFiles(directory=DOWNLOAD_DIR), name="files")

# ─────────────── الصفحة الرئيسية ───────────────
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

# ─────────────── فحص الصحة ───────────────
@app.get("/health", tags=["System"])
async def health():
    return {
        "name": API_NAME,
        "owner": API_OWNER,
        "version": API_VERSION,
        "status": "running",
        "time": datetime.now().isoformat(),
    }

# ─────────────── معلومات الفيديو ───────────────
@app.post("/youtube/info", tags=["YouTube"])
async def youtube_info(
    payload: VideoInfoRequest,
    _: str = Header(None, alias="x-api-key"),
):
    if _ != API_KEY:
        raise HTTPException(status_code=401, detail="API Key غير صحيح")

    try:
        info = get_video_info(str(payload.url))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "title": info.get("title"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "upload_date": info.get("upload_date"),
        "thumbnail": info.get("thumbnail"),
        "description": (info.get("description") or "")[:300],
        "formats_count": len(info.get("formats", [])),
    }

# ─────────────── تنزيل الفيديو ───────────────
@app.post("/youtube/download", response_model=DownloadResponse, tags=["YouTube"])
async def youtube_download(
    payload: DownloadRequest,
    _: str = Header(None, alias="x-api-key"),
):
    if _ != API_KEY:
        raise HTTPException(status_code=401, detail="API Key غير صحيح")

    try:
        result = download_video(
            url=str(payload.url),
            quality=payload.quality,
            audio_only=payload.audio_only,
            playlist=payload.playlist,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result.get("type") == "playlist":
        return DownloadResponse(
            status="success",
            message=f"تم تنزيل {result['count']} فيديو من القائمة",
            title=result.get("title"),
        )

    return DownloadResponse(
        status="success",
        message="تم التنزيل بنجاح",
        title=result.get("title"),
        filename=result.get("filename"),
        download_url=f"/files/{result.get('filename')}",
    )

# ─────────────── قائمة الملفات ───────────────
@app.get("/files-list", tags=["System"])
async def list_files(_: str = Header(None, alias="x-api-key")):
    if _ != API_KEY:
        raise HTTPException(status_code=401, detail="API Key غير صحيح")

    files = []
    for f in DOWNLOAD_DIR.iterdir():
        if f.is_file():
            files.append({
                "name": f.name,
                "size_mb": round(f.stat().st_size / 1024 / 1024, 2),
                "url": f"/files/{f.name}",
            })
    return {"count": len(files), "files": files}

# ═══════════════════════════════════════════════
# ▶️ التشغيل
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    print(f"""
╔══════════════════════════════════════════════╗
║  🎬 {API_NAME}
║  👤 Owner: {API_OWNER}
║  🌐 http://localhost:8000
║  📘 Docs:  http://localhost:8000/docs
║  🔑 API Key: {API_KEY}
╚══════════════════════════════════════════════╝
    """)
    uvicorn.run(app, host="0.0.0.0", port=8000)
