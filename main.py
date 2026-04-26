import discord
import os
from discord.ext import commands
from dotenv import load_dotenv

from commands import setup_commands

# Carrega o Token
load_dotenv()
TOKEN = os.getenv('Token')

if not TOKEN:
    raise ValueError("Erro: Token não encontrado no arquivo .env")


# Configuração do Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


# Registra os comandos
setup_commands(bot)

@bot.event
async def on_ready():
    print(f'Bot logado como \n ID:{bot.user}')

if __name__ == "__main__":
    bot.run(TOKEN)
