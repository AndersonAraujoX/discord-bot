import asyncio
import yt_dlp
from typing import Optional, List

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

async def search_songs(query: str, limit: int = 5) -> List[dict]:
    """Retorna uma lista de candidatos para a busca."""
    loop = asyncio.get_event_loop()
    # Força a busca no YouTube se não for URL
    search_query = f"ytsearch{limit}:{query}" if not query.startswith("http") else query
    
    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
        try:
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(search_query, download=False)
            )
            
            results = []
            entries = info.get("entries", [info] if "url" in info else [])
            
            for entry in entries:
                if not entry: continue
                results.append({
                    "source": entry.get("url"),
                    "title": entry.get("title"),
                    "thumbnail": entry.get("thumbnail", ""),
                    "webpage_url": entry.get("webpage_url", ""),
                    "duration": entry.get("duration", 0)
                })
            return results[:limit]
        except Exception as e:
            print(f"Erro Search YTDL: {e}")
            return []
