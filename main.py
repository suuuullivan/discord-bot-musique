# pyright: reportGeneralTypeIssues=false
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os
import sys
import shutil
from keep_alive import keep_alive

keep_alive()

# Vérifie si ffmpeg est installé
print("FFmpeg path:", shutil.which("ffmpeg"))

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("Le token n'est pas défini ! Vérifie le nom dans tes secrets Replit.")
    sys.exit()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} commandes slash synchronisées.")
    except Exception as e:
        print(f"Erreur lors de la sync des commandes : {e}")

@bot.tree.command(name="video", description="Joue une vidéo YouTube dans le salon vocal")
@app_commands.describe(url="Lien de la vidéo YouTube")
async def video(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    member = interaction.user
    if not isinstance(member, discord.Member):
        await interaction.followup.send("Impossible de déterminer ton statut vocal.")
        return

    voice = member.voice
    if not voice or not voice.channel:
        await interaction.followup.send("Tu dois être dans un salon vocal.")
        return

    try:
        vc = await voice.channel.connect()

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'cookiefile': 'www.youtube.com_cookies.txt'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Nettoie l'URL pour éviter les erreurs de format
            clean_url = url.strip()
            info = ydl.extract_info(clean_url, download=False)
            audio_url = info.get('url') or (info['formats'][0]['url'] if 'formats' in info else None)

        if not audio_url:
            await interaction.followup.send("Impossible d’extraire l’audio de cette vidéo.")
            await vc.disconnect()
            return

        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        vc.play(source)

        await interaction.followup.send("Lecture en cours.")

        while vc.is_playing():
            await asyncio.sleep(1)

        await vc.disconnect()

    except Exception as e:
        print(f"Erreur pendant /video : {e}")
        await interaction.followup.send(f"Erreur pendant la lecture : {e}")
        vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
        if vc and vc.is_connected():
            await vc.disconnect()

@bot.tree.command(name="stop", description="Arrête la lecture et quitte le salon vocal")
async def stop(interaction: discord.Interaction):
    member = interaction.user
    if not isinstance(member, discord.Member):
        await interaction.response.send_message("Impossible d'identifier ton salon vocal.", ephemeral=True)
        return

    voice = member.voice
    if not voice or not voice.channel:
        await interaction.response.send_message("Tu dois être dans un salon vocal.", ephemeral=True)
        return

    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if vc and vc.is_connected():
        await vc.disconnect()
        await interaction.response.send_message("Lecture stoppée.")
    else:
        await interaction.response.send_message("Je ne suis connecté à aucun salon vocal.")

try:
    bot.run(TOKEN)
except Exception as e:
    print(f"Erreur lors du démarrage du bot : {e}")
    sys.exit()
