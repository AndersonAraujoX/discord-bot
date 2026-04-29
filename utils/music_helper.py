import asyncio
import yt_dlp
from typing import Optional

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

async def extract_song_info(query: str) -> Optional[dict]:
    """Extrai informações da música de forma assíncrona."""
    loop = asyncio.get_event_loop()
    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
        try:
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(query, download=False)
            )
            if "entries" in info:
                info = info["entries"][0]
            
            return {
                "source": info["url"], 
                "title": info["title"],
                "thumbnail": info.get("thumbnail", ""),
                "webpage_url": info.get("webpage_url", ""),
                "duration": info.get("duration", 0)
            }
        except Exception as e:
            print(f"Erro YTDL: {e}")
            return None
