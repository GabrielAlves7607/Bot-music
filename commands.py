import discord
from discord.ext import commands
import yt_dlp
import asyncio
import psutil
import os
import gc

listamsc = []

# Configurações do yt-dlp e FFmpeg
# 1. Usada para ler playlists na velocidade da luz (pega só os dados rasos)
# Opção RÁPIDA: Apenas para listar os nomes das músicas da playlist
YDL_OPTIONS_RAPIDA = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'extract_flat': 'in_playlist', # AQUI está o segredo da velocidade
    'quiet': True,
    'ignoreerrors': True,
    'no_warnings': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Opção COMPLETA: Usada apenas no momento que a música vai começar a tocar
YDL_OPTIONS_TOCAR = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'javascript_runtimes': ['node', 'deno'],
    'remote_components': ['ejs:github'],
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

# ... (suas configurações de YDL e FFMPEG continuam as mesmas) ...

class ControleMusica(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Pausar/Retomar", style=discord.ButtonStyle.blurple, emoji="⏯️")
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("Não estou em um canal de voz.", ephemeral=True)

        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Música pausada!", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Música retomada!", ephemeral=True)
        else:
            await interaction.response.send_message("Não há nada tocando.", ephemeral=True)

    @discord.ui.button(label="Pular", style=discord.ButtonStyle.gray, emoji="⏭️")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ Música pulada!", ephemeral=True)
        else:
            await interaction.response.send_message("Fila vazia ou nada tocando.", ephemeral=True)

    @discord.ui.button(label="Parar", style=discord.ButtonStyle.red, emoji="⏹️")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            global listamsc
            listamsc.clear()
            await vc.disconnect()
            await interaction.response.send_message("⏹️ Bot desconectado e fila limpa.", ephemeral=True)

# --- COMANDOS ---
def setup_commands(bot):
    @bot.command(name="play")
    async def play(ctx, *, search: str):
        loop = asyncio.get_running_loop()

        async def carregar_e_tocar():
            if len(listamsc) > 0:
                try:
                    proxima = listamsc.pop(0)
                    
                    with yt_dlp.YoutubeDL(YDL_OPTIONS_TOCAR) as ydl:
                        info = await loop.run_in_executor(None, lambda: ydl.extract_info(proxima['url'], download=False))
                        audio_url = info['url']

                    source = discord.FFmpegOpusAudio(audio_url, **FFMPEG_OPTIONS)
                    view = ControleMusica(bot)
                    
                    ctx.voice_client.play(source, after=lambda e: ctx.bot.loop.create_task(carregar_e_tocar()))
                    
                    # Anuncia a música com os botões
                    await ctx.send(f"🎶 Tocando agora: **{proxima['title']}**", view=view)
                    
                    gc.collect()
                except Exception as e:
                    print(f"Erro ao tocar: {e}")
                    ctx.bot.loop.create_task(carregar_e_tocar())

        if not ctx.author.voice:
            return await ctx.send("Você precisa estar em um canal de voz!")
        
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()

        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS_RAPIDA) as ydl:
                try:
                    busca = search if search.startswith("http") else f"ytsearch:{search}"
                    resultados = await loop.run_in_executor(None, lambda: ydl.extract_info(busca, download=False))
                    
                    if 'entries' not in resultados or not resultados['entries']:
                        return await ctx.send("❌ Não encontrei resultados.")

                    entradas = resultados['entries'] if 'entries' in resultados else [resultados]
                    
                    if len(entradas) > 1:
                        for video in entradas:
                            if video:
                                listamsc.append({
                                    'title': video.get('title', 'Sem título'), 
                                    'url': video.get('url') or f"https://www.youtube.com/watch?v={video.get('id')}"
                                })
                        await ctx.send(f"📚 Adicionadas **{len(entradas)}** músicas!")
                    else:
                        video = entradas[0]
                        listamsc.append({'title': video['title'], 'url': video['url']})
                        if ctx.voice_client.is_playing():
                            await ctx.send(f"✅ **{video['title']}** adicionada à fila!")

                    # Inicia a reprodução se o bot estiver parado
                    if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                        await carregar_e_tocar()

                except Exception as e:
                    await ctx.send(f"Erro no processamento: {e}")

    # --- COMANDOS AUXILIARES ---
    @bot.command(name="skip")
    async def skip_cmd(ctx):
        if ctx.voice_client and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            ctx.voice_client.stop()
            await ctx.send("Musica pulada! ⏭️")
        else:
            await ctx.send("Não há nada tocando no momento.")

    @bot.command(name="stop")
    async def stop_cmd(ctx):
        if ctx.voice_client:
            listamsc.clear()
            await ctx.voice_client.disconnect()
            await ctx.send("Música parada e bot desconectado! ⏹️")
        else:
            await ctx.send("Eu não estou em um canal de voz.")

    @bot.command(name="fila")
    async def fila(ctx):
        if not listamsc:
            return await ctx.send("A fila está vazia no momento! 📭")

        embed = discord.Embed(title="📜 Fila de Músicas", color=discord.Color.green())
        lista_texto = "\n".join([f"**{i+1}.** {m['title']}" for i, m in enumerate(listamsc[:10])])
        if len(listamsc) > 10:
            lista_texto += f"\n\n*E mais {len(listamsc)-10} músicas...*"
        
        embed.description = lista_texto
        await ctx.send(embed=embed)

    @bot.command(name="status")
    async def status(ctx):
        process = psutil.Process(os.getpid())
        mem = process.memory_info().rss / 1024 / 1024
        embed = discord.Embed(title="📊 Status do Sistema", color=discord.Color.gold())
        embed.add_field(name="RAM", value=f"`{mem:.2f} MB` / 100 MB", inline=False)
        barra = "🟦" * int(mem/10) + "⬜" * (10 - int(mem/10))
        embed.add_field(name="Carga", value=barra, inline=False)
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
