import asyncio
import os
from google import genai
from google.genai import types
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

    async def transcribe_audio(self, file_path: str, segments_info: list = None, language: str = "pt") -> str:
        """
        Transcreve um arquivo de áudio WAV usando o modelo Gemini.
        Caso fornecido segments_info, auxilia a contextualizar o diálogo dos oradores.
        """
        if not os.path.exists(file_path):
            return "Erro: arquivo de áudio não encontrado."

        with open(file_path, "rb") as f:
            audio_bytes = f.read()

        # Constrói o prompt com informações de diarização/contexto se disponíveis
        prompt = (
            f"Você é um transcritor profissional de áudio de sessões de RPG de mesa em {language}.\n"
            "Sua tarefa é transcrever o áudio fornecido com máxima precisão.\n"
            "Importante:\n"
            "- Identifique os diferentes oradores e separe a fala de cada um formatando como um script ou roteiro teatral (ex: 'Jogador 1: Olá').\n"
            "- Não invente falas que não existam.\n"
            "- Ignore ruídos de fundo estáticos ou sussurros inaudíveis.\n"
        )
        
        if segments_info:
            prompt += (
                "\nAqui está uma dica cronológica de quem estava ativando o microfone (fala ativa) durante a gravação:\n"
            )
            for seg in segments_info:
                prompt += f"- Relativo {seg['start']:.1f}s a {seg['end']:.1f}s: {seg['user']}\n"
            prompt += "\nUse essas informações de timestamps para mapear quem falou qual parte no diálogo do áudio."

        # Como a chamada é síncrona de E/S de rede no SDK do genai, rodamos em thread assíncrona
        def call_gemini():
            return self._client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=audio_bytes,
                        mime_type="audio/wav"
                    )
                ]
            )

        try:
            response = await asyncio.to_thread(call_gemini)
            return response.text
        except Exception as e:
            return f"Erro na chamada da API do Gemini para transcrição: {e}"
