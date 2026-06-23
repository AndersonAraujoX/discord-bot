"""
cogs/gravar.py — Cog para gravação e transcrição de chamadas de voz
==================================================================
Implementa os comandos de barra (/gravar_iniciar e /gravar_parar).
"""

import os
import tempfile
import discord
from discord import app_commands
from discord.ext import commands
from utils.voice_helper import (
    VoiceRecorderSink,
    mix_and_downsample_packets,
    extract_speaker_segments,
    save_mono_wav,
    HAS_VOICE_RECV
)
from utils.ai_helper import AIHelper
from config import GEMINI_ENABLED

try:
    from discord.ext import voice_recv
except ImportError:
    pass


class GravarCog(commands.Cog, name="Gravação"):
    """Comandos para gravar chamadas de voz e transcrever o áudio em texto."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ai = AIHelper() if GEMINI_ENABLED else None
        self.active_recordings = {} # guild_id -> VoiceRecorderSink

    @app_commands.command(name="gravar_iniciar", description="Inicia a gravação de voz no canal atual.")
    async def gravar_iniciar(self, interaction: discord.Interaction) -> None:
        """Inicia a gravação de voz no canal em que o usuário está conectado."""
        if not HAS_VOICE_RECV:
            return await interaction.response.send_message(
                "❌ A biblioteca `discord-ext-voice-recv` não está instalada no ambiente. Gravação indisponível.",
                ephemeral=True
            )

        if not interaction.user.voice:
            return await interaction.response.send_message(
                "❌ Você precisa estar em um canal de voz para iniciar a gravação.",
                ephemeral=True
            )

        guild_id = interaction.guild.id
        if guild_id in self.active_recordings:
            return await interaction.response.send_message(
                "⚠️ Já existe uma gravação ativa neste servidor. Use `/gravar_parar` primeiro.",
                ephemeral=True
            )

        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        await interaction.response.defer()

        # Desconecta o voice client atual se ele não for compatível com recepção de áudio
        if voice_client:
            if not isinstance(voice_client, voice_recv.VoiceRecvClient):
                try:
                    await voice_client.disconnect()
                except Exception:
                    pass
                voice_client = None

        try:
            if not voice_client:
                voice_client = await channel.connect(cls=voice_recv.VoiceRecvClient)
            
            sink = VoiceRecorderSink()
            voice_client.listen(sink)
            self.active_recordings[guild_id] = sink

            await interaction.followup.send(
                f"🎙️ **Gravação iniciada** no canal **{channel.name}**!\n"
                "Para finalizar e transcrever, use `/gravar_parar`.\n"
                "*(Por favor, respeite a privacidade dos participantes e garanta o consentimento de todos)*"
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Falha ao iniciar gravação: `{e}`")

    @app_commands.command(name="gravar_parar", description="Para a gravação ativa e transcreve o texto.")
    async def gravar_parar(self, interaction: discord.Interaction) -> None:
        """Para a gravação de voz ativa, processa e transcreve o áudio gerado."""
        guild_id = interaction.guild.id

        if guild_id not in self.active_recordings:
            return await interaction.response.send_message(
                "❌ Nenhuma gravação ativa neste servidor.",
                ephemeral=True
            )

        # Defer immediately to allow processing time
        await interaction.response.defer()

        voice_client = interaction.guild.voice_client
        sink = self.active_recordings.pop(guild_id)

        # Para a escuta e desconecta
        if voice_client and isinstance(voice_client, voice_recv.VoiceRecvClient):
            try:
                voice_client.stop_listening()
            except Exception:
                pass
            try:
                await voice_client.disconnect()
            except Exception:
                pass

        if not sink.packets:
            return await interaction.followup.send(
                "⚠️ Gravação encerrada, mas nenhum pacote de voz foi capturado."
            )

        try:
            # 1. Realiza a mixagem e conversão para mono 16kHz
            mixed_pcm = mix_and_downsample_packets(sink.packets, sink.start_time)
            
            # 2. Salva em um arquivo WAV temporário
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                filepath = temp_wav.name
            
            save_mono_wav(mixed_pcm, filepath)

            # 3. Extrai segmentos de falantes para diarização contextual
            segments = extract_speaker_segments(sink.packets, sink.start_time)

            # 4. Transcreve com Gemini
            await interaction.followup.send("⏳ Processando áudio e gerando transcrição com a inteligência artificial...")
            
            if self.ai:
                transcript = await self.ai.transcribe_audio(filepath, segments)
            else:
                transcript = "⚠️ API do Gemini não configurada (sem GOOGLE_API_KEY no .env)."

            # 5. Apresenta o resultado (no chat ou como anexo se for muito grande)
            if len(transcript) < 1800:
                await interaction.channel.send(f"🎙️ **Transcrição da Chamada:**\n\n{transcript}")
            else:
                # Salva a transcrição longa em um arquivo txt temporário
                with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False, encoding="utf-8") as temp_txt:
                    temp_txt.write(transcript)
                    temp_txt_path = temp_txt.name
                
                file = discord.File(temp_txt_path, filename="transcricao_completa.txt")
                await interaction.channel.send(
                    "🎙️ A transcrição ficou muito longa e foi salva como arquivo anexo:",
                    file=file
                )
                
                try:
                    os.remove(temp_txt_path)
                except:
                    pass

            # Limpa o arquivo WAV temporário do disco
            try:
                os.remove(filepath)
            except:
                pass

        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao processar gravação e transcrição: `{e}`")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GravarCog(bot))
