import discord
import requests
import os
from discord.ext import commands, tasks
from dotenv import load_dotenv


Token = os.getenv('Token')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command(name="hoje")
async def mandar_agora(ctx):
    await ctx.send("Envio manual processado! 🚀")


bot.run(Token)

