import asyncio
import yt_dlp
import aiohttp
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

async def get_yt_suggestions(query: str) -> List[str]:
    """Busca sugestões de termos do YouTube enquanto o usuário digita."""
    if not query: return []
    url = f"https://suggestqueries.google.com/complete/search?client=youtube&ds=yt&q={query}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    # O formato é: window.google.ac.h(["query",[["sug1",0],["sug2",0]]...])
                    import json
                    # Extração simples via regex ou fatiamento
                    start = text.find("(") + 1
                    end = text.rfind(")")
                    data = json.loads(text[start:end])
                    return [s[0] for s in data[1]]
        except:
            pass
    return []
