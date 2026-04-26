import discord
from discord.ext import commands
import yt_dlp
import asyncio

listamsc = []

# Configurações do yt-dlp e FFmpeg
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': 'True',
    'quiet': True,
    'no_warnings': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

def setup_commands(bot):
    @bot.command(name="play")
    async def play(ctx, *, search: str):
        def tocar_proxima(error): # Adicionamos o 'error' aqui
            if len(listamsc) > 0:
                # 1. Pega a URL que estava guardada na fila
                proxima_url = listamsc.pop(0) 
                
                # 2. Cria o source SEM o await e usando a proxima_url
                source = discord.FFmpegPCMAudio(proxima_url, **FFMPEG_OPTIONS)
                
                # 3. Toca e avisa que, quando acabar, chama o fiscal de novo
                ctx.voice_client.play(source, after=tocar_proxima)
            else:
                # Se a lista estiver vazia, o fiscal vai dormir
                pass

        """Toca uma música baseada no link ou termo de busca."""
        if not ctx.author.voice:
            return await ctx.send("Você precisa estar em um canal de voz!")

        # Conecta ao canal se não estiver conectado
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()

        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                try:
                    # 1. Busca os dados da música
                    info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
                    url = info['url']
                    title = info['title']
                    
                    if not ctx.voice_client.is_playing():
                        # A caixa está livre! Criamos o áudio e damos o play.
                        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
                        ctx.voice_client.play(source, after=tocar_proxima)
                        await ctx.send(f"🎵 Tocando agora: **{title}**")
                    else:
                        # A caixa está ocupada! APENAS guardamos a URL na lista.
                        listamsc.append(url)
                        await ctx.send(f"🎵 Adicionada à fila: **{title}** (Posição: {len(listamsc)})")

                except Exception as e:
                    await ctx.send(f"Erro ao tentar processar a música: {e}")

    @bot.command(name="stop")
    async def stop(ctx):
        """Para a música e desconecta."""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Música parada e bot desconectado! ⏹️")
        else:
            await ctx.send("Eu não estou tocando nada no momento.")

    @bot.command(name="pause")
    async def pause(ctx):
        """Pausa a música atual."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Música pausada! ⏸️")

    @bot.command(name="resume")
    async def resume(ctx):
        """Retoma a música pausada."""
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Música retomada! ▶️")

    @bot.command(name="help")
    async def help_command(ctx):
        """Exibe a lista de comandos de forma elegante."""
        embed = discord.Embed(
            title="🎵 Central de Ajuda - Bot Music",
            description="Aqui estão os comandos disponíveis para você aproveitar a música!",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="▶️ `!play [música/link]`",
            value="Busca e toca uma música do YouTube.",
            inline=False
        )
        embed.add_field(
            name="⏸️ `!pause`",
            value="Pausa a reprodução atual.",
            inline=True
        )
        embed.add_field(
            name="⏯️ `!resume`",
            value="Retoma a música pausada.",
            inline=True
        )
        embed.add_field(
            name="⏹️ `!stop`",
            value="Para a música e desconecta o bot.",
            inline=False
        )
        
        embed.set_footer(text="Aproveite a sua música! 🎧", icon_url=ctx.bot.user.avatar.url if ctx.bot.user.avatar else None)
        embed.set_thumbnail(url=ctx.bot.user.avatar.url if ctx.bot.user.avatar else None)

        await ctx.send(embed=embed)
