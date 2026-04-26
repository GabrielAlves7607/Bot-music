from discord.ext import commands
import nacl.utils


def setup_commands(bot):
    @bot.command(name="play")

    async def play(ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            await ctx.send(f"Conectado a {channel}! 🎶")
        else:
            await ctx.send("Você precisa estar em um canal de voz para usar este comando!")

    @bot.command(name="stop")
    async def stop(ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Desconectado! 🚪")
        else:
            await ctx.send("Eu não estou em nenhum canal de voz.")

