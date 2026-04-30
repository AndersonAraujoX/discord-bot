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
    """Retorna uma lista de candidatos. Se for link, busca o título e versões alternativas."""
    loop = asyncio.get_event_loop()
    
    is_url = query.startswith("http")
    results = []

    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
        try:
            # 1. Se for URL, pega a info da URL primeiro
            if is_url:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
                if "entries" in info: info = info["entries"][0]
                
                original = {
                    "source": info.get("url"),
                    "title": f"🔗 Original: {info.get('title')}",
                    "thumbnail": info.get("thumbnail", ""),
                    "webpage_url": info.get("webpage_url", ""),
                    "duration": info.get("duration", 0)
                }
                results.append(original)
                # Usa o título para buscar alternativas
                query = info.get("title")

            # 2. Busca termos (ou alternativas se veio de URL)
            search_query = f"ytsearch{limit}:{query}"
            info_search = await loop.run_in_executor(None, lambda: ydl.extract_info(search_query, download=False))
            
            entries = info_search.get("entries", [])
            for entry in entries:
                if not entry: continue
                # Evita duplicar o original se for exatamente o mesmo título/url
                if is_url and entry.get("webpage_url") == results[0]["webpage_url"]:
                    continue
                    
                results.append({
                    "source": entry.get("url"),
                    "title": entry.get("title"),
                    "thumbnail": entry.get("thumbnail", ""),
                    "webpage_url": entry.get("webpage_url", ""),
                    "duration": entry.get("duration", 0)
                })
                
            return results[:limit]
        except Exception as e:
            print(f"Erro Search/URL YTDL: {e}")
            return results # Retorna o que conseguiu (pode ser só o original)

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
