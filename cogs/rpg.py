import asyncio
import discord
from discord.ext import commands
from utils.ai_helper import AIHelper
from config import GEMINI_ENABLED

_INTRO_PROMPT = (
    "Apresente-se brevemente aos aventureiros que acabaram de te encontrar, "
    "mantendo sua personalidade."
)

class RpgCog(commands.Cog, name="IA RPG"):
    """Sessões de RPG imersivas com IA Gemini."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ai = AIHelper() if GEMINI_ENABLED else None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not self.ai or message.author.bot or not message.guild:
            return
        
        if not self.ai.is_active(message.guild.id):
            return
            
        if not self.bot.user.mentioned_in(message):
            return

        prompt = (
            message.content
            .replace(f"<@!{self.bot.user.id}>", "")
            .replace(f"<@{self.bot.user.id}>", "")
            .strip()
        )
        if not prompt: return

        async with message.channel.typing():
            try:
                response = await self.ai.ask(message.guild.id, prompt)
                await message.reply(response)
            except Exception as exc:
                await message.channel.send(f"❌ Erro na IA: `{exc}`")

    @app_commands.command(name="rpg_start", description="Inicia uma sessão de RPG com o personagem Rilem/Miler.")
    async def rpg_start(self, interaction: discord.Interaction) -> None:
        """Inicia uma sessão de RPG com o personagem Rilem/Miler."""
        if not self.ai:
            return await interaction.response.send_message("❌ RPG desabilitado.", ephemeral=True)
            
        if self.ai.is_active(interaction.guild.id):
            return await interaction.response.send_message("Já há uma sessão ativa. Use `/rpg_stop`.", ephemeral=True)

        await interaction.response.defer()
        try:
            self.ai.start_session(interaction.guild.id)
            inicial = await self.ai.ask(interaction.guild.id, _INTRO_PROMPT)
            await interaction.followup.send(
                f"**Sessão de RPG iniciada!** O bot agora é **Rilem/Miler**.\n\n"
                f"> {inicial}\n\n"
                f"*Mencione-me (@{self.bot.user.name}) para interagir.*"
            )
        except Exception as exc:
            await interaction.followup.send(f"❌ Erro ao iniciar: `{exc}`")

    @app_commands.command(name="rpg_stop", description="Encerra a sessão de RPG ativa.")
    async def rpg_stop(self, interaction: discord.Interaction) -> None:
        """Encerra a sessão de RPG ativa."""
        if self.ai and self.ai.is_active(interaction.guild.id):
            self.ai.stop_session(interaction.guild.id)
            await interaction.response.send_message("Sessão encerrada. Voltei ao modo normal. 🤖")
        else:
            await interaction.response.send_message("Nenhuma sessão ativa.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RpgCog(bot))
