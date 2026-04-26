import discord
from discord.ext import commands
import yt_dlp
import asyncio
import psutil
import os
import gc

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
    # Antes de abrir o link: focado em estabilidade e velocidade de conexão
    'before_options': (
        '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 '
        '-nostdin -ss 0'
    ),
    # Durante o processamento: focado em qualidade e baixa latência
    'options': (
        '-vn -loglevel panic '
        '-b:a 128k '                # Força bitrate de 128kbps (alta qualidade para voz)
        '-ar 48000 '                # Sample rate nativo do Discord (48kHz)
        '-ac 2 '                    # Estéreo
        '-threads 0 '               # Usa todos os núcleos da CPU para processar
        '-analyzeduration 0 '       # Início instantâneo
        '-probesize 32 '            # Investigação mínima do arquivo
        '-af "volume=1.0"'          # Filtro de áudio (volume normalizado)
    )
}

def setup_commands(bot):
    @bot.command(name="play")
    async def play(ctx, *, search: str):
        def tocar_proxima(error):
            if len(listamsc) > 0:
                # 1. Pega os dados da próxima música
                proxima_musica = listamsc.pop(0) 
                proxima_url = proxima_musica['url']
                
                # 2. Cria o source
                source = discord.FFmpegPCMAudio(proxima_url, **FFMPEG_OPTIONS)
                
                # 3. Toca a próxima
                ctx.voice_client.play(source, after=tocar_proxima)
                gc.collect() # Limpa resíduos da música anterior da RAM

        """Toca uma música baseada no link ou termo de busca."""
        if not ctx.author.voice:
            return await ctx.send("Você precisa estar em um canal de voz!")

        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()

        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                try:
                    info = ydl.extract_info(f"ytsearch:{search}", download=False)['entries'][0]
                    url = info['url']
                    title = info['title']
                    
                    if not ctx.voice_client.is_playing():
                        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
                        ctx.voice_client.play(source, after=tocar_proxima)
                        await ctx.send(f"🎵 Tocando agora: **{title}**")
                    else:
                        # Salvamos o título e a URL
                        listamsc.append({'title': title, 'url': url})
                        await ctx.send(f"🎵 Adicionada à fila: **{title}** (Posição: {len(listamsc)})")

                except Exception as e:
                    await ctx.send(f"Erro ao tentar processar a música: {e}")

    @bot.command(name="skip")
    async def skip(ctx):
        """Pular musicas"""
        if ctx.voice_client.is_playing() and ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.send("Musica pulada! ⏭️ ")
        else:
            await ctx.send("Não há nada tocando no momento.")

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

    @bot.command(name="fila")
    async def fila(ctx):
        """Lista as músicas na fila."""
        if len(listamsc) == 0:
            return await ctx.send("A fila está vazia no momento! 📭")

        embed = discord.Embed(
            title="📜 Fila de Músicas",
            description=f"Existem **{len(listamsc)}** músicas na fila.",
            color=discord.Color.green()
        )

        lista_texto = ""
        for i, musica in enumerate(listamsc[:10], 1):
            lista_texto += f"**{i}.** {musica['title']}\n"

        if len(listamsc) > 10:
            lista_texto += f"\n*E mais {len(listamsc) - 10} músicas...*"

        embed.add_field(name="Próximas músicas:", value=lista_texto, inline=False)
        await ctx.send(embed=embed)

    @bot.command(name="status")
    async def status(ctx):
        """Mostra o uso atual de RAM do bot."""
        process = psutil.Process(os.getpid())
        memoria_mb = process.memory_info().rss / 1024 / 1024
        
        embed = discord.Embed(
            title="📊 Status do Sistema",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Uso de Memória RAM",
            value=f"`{memoria_mb:.2f} MB` / 100 MB",
            inline=False
        )
        
        # Barra visual simples
        barra_cheia = min(int((memoria_mb / 100) * 10), 10)
        barra_vazia = 10 - barra_cheia
        grafico = "🟦" * barra_cheia + "⬜" * barra_vazia
        
        embed.add_field(name="Carga", value=grafico, inline=False)
        
        await ctx.send(embed=embed)

    @bot.command(name="help")
    async def help_command(ctx):
        """Exibe a lista de comandos de forma elegante."""
        embed = discord.Embed(
            title="🎵 Central de Ajuda - Bot Music",
            description="Aqui estão os comandos disponíveis para você aproveitar a música!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📜 `!fila`",
            value="Mostra a lista de músicas aguardando.",
            inline=False
        )
        embed.add_field(
            name="📊 `!status`",
            value="Mostra o uso de RAM do bot.",
            inline=False
        )
        embed.add_field(
            name="▶️ `!play [música/link]`",
            value="Busca e toca uma música do YouTube.",
            inline=False
        )
        embed.add_field(
            name="⏭️ `!skip`",
            value="Pular para a próxima música.",
            inline=False
        )
        embed.add_field(
            name="⏸️ `!pause`",
            value="Pausa a reprodução atual.",
            inline=False
        )
        embed.add_field(
            name="⏯️ `!resume`",
            value="Retoma a música pausada.",
            inline=False
        )
        embed.add_field(
            name="⏹️ `!stop`",
            value="Para a música e desconecta o bot.",
            inline=False
        )

        
        embed.set_footer(text="Aproveite a sua música! 🎧", icon_url=ctx.bot.user.avatar.url if ctx.bot.user.avatar else None)
        embed.set_thumbnail(url=ctx.bot.user.avatar.url if ctx.bot.user.avatar else None)

        await ctx.send(embed=embed)
