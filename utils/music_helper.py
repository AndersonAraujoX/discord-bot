import asyncio
import yt_dlp
import aiohttp
from pathlib import Path
from typing import Optional, List
import yt_dlp
import aiohttp

from config import COOKIES_PATH


def get_ytdl_options(custom_cookies: Optional[Path] = None) -> dict:
    """Gera as opções do yt-dlp com suporte a clientes móveis e cookies."""
    opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web_creator']
            }
        }
    }
    cookie_file = custom_cookies if custom_cookies is not None else COOKIES_PATH
    if cookie_file and Path(cookie_file).is_file():
        opts['cookiefile'] = str(cookie_file)
    return opts


YTDL_OPTIONS = get_ytdl_options()


async def extract_song_info(query: str, options: Optional[dict] = None) -> Optional[dict]:
    """Extrai informações da música de forma assíncrona com fallback."""
    if not query:
        return None
    opts = options or get_ytdl_options()
    loop = asyncio.get_event_loop()
    
    # 1. Tentativa padrão (YouTube com extractor_args móveis)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(query, download=False)
            )
            if info and "entries" in info and info["entries"]:
                info = info["entries"][0]
            
            if info and info.get("url"):
                return {
                    "source": info["url"], 
                    "title": info.get("title", "Desconhecido"),
                    "thumbnail": info.get("thumbnail", ""),
                    "webpage_url": info.get("webpage_url", ""),
                    "duration": info.get("duration", 0)
                }
    except Exception as e:
        print(f"Erro YTDL no extract_song_info: {e}")

    # 2. Fallback para SoundCloud se não for URL direta
    if not query.startswith("http"):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = await loop.run_in_executor(
                    None, lambda: ydl.extract_info(f"scsearch1:{query}", download=False)
                )
                if info and "entries" in info and info["entries"]:
                    info = info["entries"][0]
                if info and info.get("url"):
                    return {
                        "source": info["url"],
                        "title": f"☁️ {info.get('title', 'Desconhecido')}",
                        "thumbnail": info.get("thumbnail", ""),
                        "webpage_url": info.get("webpage_url", ""),
                        "duration": info.get("duration", 0)
                    }
        except Exception as e_sc:
            print(f"Erro Fallback SoundCloud extract_song_info: {e_sc}")

    return None


async def search_songs(query: str, limit: int = 5, options: Optional[dict] = None) -> List[dict]:
    """Retorna uma lista de candidatos. Se for link, busca o título e versões alternativas com fallback SoundCloud."""
    if not query:
        return []
    loop = asyncio.get_event_loop()
    opts = options or get_ytdl_options()
    is_url = query.startswith("http")
    results = []

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            # 1. Se for URL, pega a info da URL primeiro
            if is_url:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
                if info and "entries" in info and info["entries"]:
                    info = info["entries"][0]
                
                if info and info.get("url"):
                    original = {
                        "source": info.get("url"),
                        "title": f"🔗 Original: {info.get('title')}",
                        "thumbnail": info.get("thumbnail", ""),
                        "webpage_url": info.get("webpage_url", ""),
                        "duration": info.get("duration", 0)
                    }
                    results.append(original)
                    query = info.get("title", query)

            # 2. Busca termos no YouTube
            search_query = f"ytsearch{limit}:{query}"
            info_search = await loop.run_in_executor(None, lambda: ydl.extract_info(search_query, download=False))
            
            entries = info_search.get("entries", []) if info_search else []
            for entry in entries:
                if not entry:
                    continue
                if is_url and results and entry.get("webpage_url") == results[0].get("webpage_url"):
                    continue
                    
                results.append({
                    "source": entry.get("url"),
                    "title": entry.get("title"),
                    "thumbnail": entry.get("thumbnail", ""),
                    "webpage_url": entry.get("webpage_url", ""),
                    "duration": entry.get("duration", 0)
                })
                
            if results:
                return results[:limit]
    except Exception as e:
        print(f"Erro Search/URL YTDL (YouTube): {e}")

    # Fallback automático para SoundCloud
    if not is_url:
        try:
            print(f"Tentando busca alternativa no SoundCloud para '{query}'...")
            with yt_dlp.YoutubeDL(opts) as ydl:
                sc_query = f"scsearch{limit}:{query}"
                info_sc = await loop.run_in_executor(None, lambda: ydl.extract_info(sc_query, download=False))
                entries = info_sc.get("entries", []) if info_sc else []
                for entry in entries:
                    if not entry:
                        continue
                    results.append({
                        "source": entry.get("url"),
                        "title": f"☁️ {entry.get('title')}",
                        "thumbnail": entry.get("thumbnail", ""),
                        "webpage_url": entry.get("webpage_url", ""),
                        "duration": entry.get("duration", 0)
                    })
                return results[:limit]
        except Exception as e_sc:
            print(f"Erro Search/URL YTDL (SoundCloud): {e_sc}")

    return results

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
