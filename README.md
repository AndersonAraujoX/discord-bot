# 🤖 Rilem/Miler Bot

Um bot multifuncional para Discord, focado em **Música**, **RPG Imersivo com IA** e **Sistemas de Dados Avançados**. Refatorado para alta performance e modularidade usando **Cogs**.

## 🌟 Funcionalidades Principais

### 🎭 RPG com Inteligência Artificial (Gemini)
O bot assume a personalidade de **Rilem/Miler**, um personagem com história profunda e dualidade de personalidade.
- Integração direta com a API **Google Gemini**.
- Mantém contexto de conversa durante sessões de RPG.
- Respostas imersivas e consistentes com o "lore" do personagem.

### 🎲 Sistema Avançado de Dados
Um motor de rolagem completo para qualquer sistema de RPG.
- **Notação Padrão:** `!roll 1d20`
- **Dados Explosivos:** `!roll d6!` (rola novamente no resultado máximo).
- **Descarte (Drop):** `!roll 4d6d1` (rola 4 dados e descarta o menor).
- **Rolagem em Massa:** `!roll 6#4d6d1` (faz 6 rolagens de uma vez com estatísticas).

### 🎵 Sistema de Música Premium
- Suporte a links do YouTube, SoundCloud e buscas por nome.
- **Fila e Loop:** Modos de repetição por música ou por fila inteira.
- **Estabilidade:** Uso de `FFmpeg` com reconexão automática e suporte a `cookies.txt`.

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** [Python 3.10+](https://www.python.org/)
- **Biblioteca Base:** [discord.py](https://discordpy.readthedocs.io/)
- **IA:** [Google GenAI (Gemini SDK)](https://ai.google.dev/)
- **Áudio:** [yt-dlp](https://github.com/yt-dlp/yt-dlp) & [FFmpeg](https://ffmpeg.org/)

## 🚀 Como Executar

1. Clone o repositório:
   ```bash
   git clone https://github.com/AndersonAraujoX/bot-discord.git
   cd bot-discord
   ```

2. Crie um ambiente virtual e instale as dependências:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux
   pip install -r requirements.txt
   ```

3. Configure as variáveis de ambiente no arquivo `.env`:
   ```env
   DISCORD_TOKEN=seu_token_aqui
   GOOGLE_API_KEY=sua_chave_gemini_aqui
   ```

4. Execute o bot:
   ```bash
   python bot.py
   ```

## 📁 Estrutura do Projeto

O código é modularizado para facilitar a manutenção:
- `cogs/`: Módulos de comandos (Musica, RPG, Dados, Geral).
- `utils/dice_engine.py`: Motor lógico das rolagens de dados.
- `config.py`: Centralização de configurações e constantes.

---
*Desenvolvido para AndersonAraujoX*
