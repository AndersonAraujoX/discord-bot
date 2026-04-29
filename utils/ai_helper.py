import asyncio
from google import genai
from config import GOOGLE_API_KEY, GEMINI_MODEL, RILEM_MILER_PROMPT

class AIHelper:
    """Helper para gerenciar conversas com a IA usando o novo SDK."""
    
    def __init__(self):
        self._client = genai.Client(api_key=GOOGLE_API_KEY)
        self._sessions = {} # guild_id -> chat_session

    def start_session(self, guild_id: int):
        chat = self._client.chats.create(
            model=GEMINI_MODEL,
            history=[{"role": "user", "parts": [RILEM_MILER_PROMPT]}],
        )
        self._sessions[guild_id] = chat
        return chat

    async def ask(self, guild_id: int, message: str) -> str:
        if guild_id not in self._sessions:
            return "Nenhuma sessão ativa."
        
        chat = self._sessions[guild_id]
        response = await asyncio.to_thread(chat.send_message, message)
        return response.text

    def stop_session(self, guild_id: int):
        if guild_id in self._sessions:
            del self._sessions[guild_id]

    def is_active(self, guild_id: int) -> bool:
        return guild_id in self._sessions
