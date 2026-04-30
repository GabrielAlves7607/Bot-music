import discord
from discord.ext import commands
import yt_dlp
import asyncio
import psutil
import os
import gc
import random

listamsc = []
loop_status = "off"
ultima_view = None 

# Configurações otimizadas para baixa RAM
YDL_OPTIONS_RAPIDA = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'extract_flat': 'in_playlist',
    'quiet': True,
    'ignoreerrors': True,
    'no_warnings': True,
    'cachedir': False,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

YDL_OPTIONS_TOCAR = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'cachedir': False,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

FFMPEG_OPTIONS = {
    'before_options': (
        '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 '
        '-nostdin -ss 0'
    ),
    'options': (
        '-vn -loglevel panic '
        '-b:a 128k '                 # Bitrate reduzido para economizar RAM
        '-ar 48000 '                # Sample rate reduzido para estabilidade
        '-ac 2 '                    
        '-threads 1 '               # FORÇA apenas 1 thread (Essencial para 100MB)
        '-analyzeduration 0 '       
        '-probesize 32 '            
        '-af "volume=1.0"'          
    )
}

class ControleMusica(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        
        global loop_status
        for item in self.children:
            if isinstance(item, discord.ui.Button) and "Loop" in (item.label or ""):
                if loop_status == "current":
                    item.style, item.label, item.emoji = discord.ButtonStyle.green, "Loop: Música", "🔂"
                elif loop_status == "queue":
                    item.style, item.label, item.emoji = discord.ButtonStyle.blurple, "Loop: Fila", "🔁"
                else:
                    item.style, item.label, item.emoji = discord.ButtonStyle.gray, "Loop: Off", "🔁"

    @discord.ui.button(label="Pausar/Retomar", style=discord.ButtonStyle.blurple, emoji="⏯️")
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Pausado", ephemeral=True)
        elif vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Retomado", ephemeral=True)
        else:
            await interaction.response.send_message("Nada tocando", ephemeral=True)

    @discord.ui.button(label="Pular", style=discord.ButtonStyle.gray, emoji="⏭️")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
            await interaction.response.send_message("⏭️ Pulada", ephemeral=True)

    @discord.ui.button(label="Loop: Off", style=discord.ButtonStyle.gray, emoji="🔁")
    async def loop_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        global loop_status
        if loop_status == "off": loop_status = "current"
        elif loop_status == "current": loop_status = "queue"
        else: loop_status = "off"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Parar", style=discord.ButtonStyle.red, emoji="⏹️")
    async def parar_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            global listamsc, ultima_view
            listamsc.clear()
            await vc.disconnect()
            if ultima_view:
                ultima_view.stop()
            await interaction.response.send_message("⏹️ Desconectado", ephemeral=True)

class buscar(discord.ui.View):
    def __init__(self, bot, indice_atual, indice_destino):
        super().__init__(timeout=60)
        self.bot = bot
        self.indice_atual = indice_atual      
        self.indice_destino = indice_destino  

    @discord.ui.button(label="Mover", style=discord.ButtonStyle.green, emoji="🔝")
    async def mover(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.indice_atual < len(listamsc):
            musica = listamsc.pop(self.indice_atual)
            destino = max(0, min(self.indice_destino, len(listamsc)))
            listamsc.insert(destino, musica)
            await interaction.response.edit_message(content=f"✅ Movida para {self.indice_destino + 1}!", view=None)

    @discord.ui.button(label="Remover", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remover(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.indice_atual < len(listamsc):
            listamsc.pop(self.indice_atual)
            await interaction.response.edit_message(content=f"🗑️ Removida!", view=None)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Cancelado ❌", view=None)

def setup_commands(bot):
    @bot.command(name="play")
    async def play(ctx, *, search: str):
        loop = asyncio.get_running_loop()

        async def carregar_e_tocar():
            global loop_status, ultima_view
            
            if loop_status == "queue" and hasattr(ctx.voice_client, 'musica_atual'):
                listamsc.append(ctx.voice_client.musica_atual)
            
            if len(listamsc) > 0 or (loop_status == "current" and hasattr(ctx.voice_client, 'musica_atual')):
                try:
                    proxima = ctx.voice_client.musica_atual if loop_status == "current" else listamsc.pop(0)
                    ctx.voice_client.musica_atual = proxima

                    with yt_dlp.YoutubeDL(YDL_OPTIONS_TOCAR) as ydl:
                        info = await loop.run_in_executor(None, lambda: ydl.extract_info(proxima['url'], download=False))
                        audio_url = info['url']
                        del info 

                    source = discord.FFmpegOpusAudio(audio_url, **FFMPEG_OPTIONS)
                    
                    if ultima_view: ultima_view.stop() 
                    view = ControleMusica(bot)
                    ultima_view = view 
                    
                    # Trava de segurança: Se der erro, espera 2 segundos antes de pular para não limpar a fila
                    def apos_tocar(error):
                        if error: print(f"❌ ERRO PLAYER: {error}")
                        async def delay_next():
                            await asyncio.sleep(2)
                            await carregar_e_tocar()
                        ctx.bot.loop.create_task(delay_next())

                    ctx.voice_client.play(source, after=apos_tocar)
                    await ctx.send(f"🎶 Tocando: **{proxima['title']}**", view=view)
                    gc.collect() 
                    
                except Exception as e:
                    print(f"🚨 ERRO EXTRAÇÃO: {e}")
                    await asyncio.sleep(2)
                    ctx.bot.loop.create_task(carregar_e_tocar())

        if not ctx.author.voice: return await ctx.send("Entre num canal de voz!")
        if not ctx.voice_client: await ctx.author.voice.channel.connect()

        async with ctx.typing():
            with yt_dlp.YoutubeDL(YDL_OPTIONS_RAPIDA) as ydl:
                try:
                    busca = search if search.startswith("http") else f"ytsearch:{search}"
                    res = await loop.run_in_executor(None, lambda: ydl.extract_info(busca, download=False))
                    entradas = res.get('entries', [res])
                    
                    for video in entradas:
                        if video:
                            # Truncamos o título para economizar memória na lista
                            listamsc.append({
                                'title': video.get('title', 'Sem título')[:50], 
                                'url': video.get('url') or f"https://www.youtube.com/watch?v={video.get('id')}"
                            })
                    
                    await ctx.send(f"📚 Adicionadas **{len(entradas)}** músicas!")
                    del res, entradas
                    gc.collect()

                    if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
                        await carregar_e_tocar()
                except Exception as e:
                    await ctx.send(f"Erro: {e}")

    @bot.command(name="find")
    async def find(ctx, *, search: str):
        p = search.split()
        indiced = int(p.pop()) - 1 if len(p) > 1 and p[-1].isdigit() else 0
        busca = " ".join(p).lower() if indiced != 0 or (len(p) > 1 and search.split()[-1].isdigit()) else search.lower()

        for indice, musica in enumerate(listamsc):
            if busca in musica['title'].lower():
                await ctx.send(f"🔎 Achei: **{musica['title']}** (# {indice + 1})", view=buscar(ctx.bot, indice, indiced))
                return
        await ctx.send("❌ Não achei.")

    @bot.command(name="status")
    async def status(ctx):
        mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
        await ctx.send(f"📊 **RAM:** `{mem:.2f} MB` / 100 MB")

    @bot.command(name="skip")
    async def skip_cmd(ctx):
        if ctx.voice_client: ctx.voice_client.stop()

    @bot.command(name="stop")
    async def stop_cmd(ctx):
        if ctx.voice_client:
            global listamsc, ultima_view
            listamsc.clear()
            await ctx.voice_client.disconnect()
            if ultima_view: ultima_view.stop()
            await ctx.send("Parado ⏹️")

    @bot.command(name="fila")
    async def fila(ctx):
        if not listamsc: return await ctx.send("Vazia 📭")
        txt = "\n".join([f"**{i+1}.** {m['title']}" for i, m in enumerate(listamsc[:10])])
        await ctx.send(embed=discord.Embed(title="📜 Fila", description=txt, color=0x00ff00))

    @bot.command(name="randomizar")
    async def shuffle_cmd(ctx):
        global listamsc
        if len(listamsc) < 2:
            return await ctx.send("Fila muito curta para embaralhar! 🤏")
        random.shuffle(listamsc)
        await ctx.send("🔀 Fila embaralhada com sucesso!")

    @bot.command(name="loop")
    async def loop_cmd(ctx):
        """Alterna entre os modos de repetição: Off -> Música -> Fila"""
        global loop_status
        
        if loop_status == "off":
            loop_status = "current"
            await ctx.send("🔂 Loop: **Música Atual** ativado!")
        elif loop_status == "current":
            loop_status = "queue"
            await ctx.send("🔁 Loop: **Fila Inteira** ativado!")
        else:
            loop_status = "off"
            await ctx.send("❌ Loop desativado!")

    @bot.command(name="limpar")
    async def clean_cmd(ctx):
        global listamsc
        listamsc.clear()
        await ctx.send("🧹 Fila limpa!")

    @bot.command(name="help")
    async def help_command(ctx):
        embed = discord.Embed(
            title="🎵 Central de Ajuda - Bot Music",
            description="Aqui estão os comandos disponíveis para você aproveitar a música!",
            color=discord.Color.blue()
        )
        embed.add_field(name="📜 `!fila`", value="Mostra a lista de músicas.", inline=False)
        embed.add_field(name="📊 `!status`", value="Mostra o uso de RAM.", inline=False)
        embed.add_field(name="▶️ `!play`", value="Toca uma música.", inline=False)
        embed.add_field(name="⏭️ `!skip`", value="Pula a música.", inline=False)
        embed.add_field(name="⏹️ `!stop`", value="Para e desconecta.", inline=False)
        embed.add_field(name="🔎 `!find`", value="Busca na fila.", inline=False)
        embed.set_footer(text="Aproveite a sua música! 🎧")
        await ctx.send(embed=embed)