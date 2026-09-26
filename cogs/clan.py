import discord
from discord import app_commands
from discord.ext import commands
from utils.ai_helper import AIHelper
from utils.clan_verifier import verify_clan_entries
from config import GEMINI_ENABLED

class ClanVerificationCog(commands.Cog, name="Verificação de Clã"):
    """Cog para gerenciar a validação automatizada de logs de entrada no clã."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ai = AIHelper() if GEMINI_ENABLED else None

    @app_commands.command(
        name="verificar_membros", 
        description="Analisa um log de clã em imagem e valida com a quantidade esperada de novos membros."
    )
    @app_commands.describe(
        quantidade_esperada="A quantidade de jogadores que você espera que tenham entrado no clã.",
        imagem="O print/screenshot do log de entrada de membros do clã."
    )
    async def verificar_membros(
        self, 
        interaction: discord.Interaction, 
        quantidade_esperada: int, 
        imagem: discord.Attachment
    ) -> None:
        if not self.ai:
            return await interaction.response.send_message(
                "❌ A funcionalidade de inteligência artificial está desabilitada no momento (GOOGLE_API_KEY ausente).",
                ephemeral=True
            )

        # Validação básica do anexo de imagem
        content_type = imagem.content_type or ""
        if not content_type.startswith("image/"):
            return await interaction.response.send_message(
                "❌ O arquivo enviado não parece ser uma imagem válida. Por favor, envie um arquivo PNG, JPG ou WEBP.",
                ephemeral=True
            )

        # Defer para evitar timeout da API do Discord (limite de 3 segundos)
        await interaction.response.defer()

        try:
            # Baixa os bytes do anexo
            image_bytes = await imagem.read()
            
            # Chama a IA para ler e processar os dados da imagem
            detected_data = await self.ai.analyze_clan_image(image_bytes, content_type)
            
            if "error" in detected_data:
                await interaction.followup.send(
                    f"❌ Ocorreu um erro ao processar a imagem com a IA:\n`{detected_data['error']}`"
                )
                return

            # Executa a lógica de validação comparando com a quantidade esperada
            resultado = verify_clan_entries(quantidade_esperada, detected_data)
            
            # Constrói a lista formatada dos membros detectados
            membros_str = ""
            for m in resultado["jogadores"]:
                nome = m.get("nome", "Desconhecido")
                data_hora = m.get("data_hora")
                if data_hora:
                    membros_str += f"👤 **{nome}** — *{data_hora}*\n"
                else:
                    membros_str += f"👤 **{nome}**\n"
            
            if not membros_str:
                membros_str = "*Nenhum jogador identificado na imagem.*"

            # Monta o Embed de resposta
            embed = discord.Embed(
                title="🔍 Verificação de Entrada no Clã",
                description=f"### {resultado['status_text']}\n\n{resultado['mensagem_detalhe']}",
                color=resultado["status_color"]
            )
            
            embed.add_field(name="Quantidade Informada", value=str(quantidade_esperada), inline=True)
            embed.add_field(name="Quantidade Detectada", value=str(resultado["total_detectado"]), inline=True)
            embed.add_field(name="Jogadores Detectados na Imagem", value=membros_str, inline=False)
            
            embed.set_footer(text=f"Solicitado por {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
            
            await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"Erro no comando verificar_membros: {e}")
            await interaction.followup.send(
                f"❌ Houve um erro inesperado ao executar a verificação: `{e}`"
            )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ClanVerificationCog(bot))
