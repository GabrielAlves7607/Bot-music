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


# Configuração do Bot com Otimização de RAM
intents = discord.Intents.default()
intents.message_content = True
intents.members = False
intents.presences = False

bot = commands.Bot(
    command_prefix='!', 
    intents=intents, 
    help_command=None,
    member_cache_flags=discord.MemberCacheFlags.none() # Não guarda membros na RAM
)


# Registra os comandos
setup_commands(bot)

@bot.event
async def on_ready():
    print(f'Bot logado como \n ID:{bot.user}')

if __name__ == "__main__":
    bot.run(TOKEN)
