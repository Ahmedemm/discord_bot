import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
import os
import requests
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
ALLOWED_GUILD_ID = int(os.getenv("GUILD_ID"))
FFMPEG_OPTIONS = os.getenv("FFMPEG_OPTIONS", "-vn -filter:a 'volume=0.5'")
PREFIX = os.getenv("DEFAULT_PREFIX", "!")
M3U_URL = os.getenv("M3U_URL")

# Configuration des intentions Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Stockage des chaînes IPTV
channels = {}
current_channel = None

def load_channels_from_m3u(m3u_content):
    """Charge les chaînes depuis un contenu M3U."""
    channels.clear()
    current_name = None
    current_info = {}
    
    for line in m3u_content.split('\n'):
        line = line.strip()
        if line.startswith('#EXTINF:'):
            # Extraire les informations de la chaîne
            info_part = line.split(',', 1)
            if len(info_part) > 1:
                current_name = info_part[1].strip()
                # Nettoyer le nom pour l'utiliser comme clé
                current_info = {
                    'display_name': current_name,
                    'key': current_name.lower().replace(' ', '_').replace('/', '_'),
                    'group': 'Unknown'
                }
                # Extraire le groupe si disponible
                if 'group-title="' in line:
                    group = line.split('group-title="')[1].split('"')[0]
                    current_info['group'] = group
        elif line and not line.startswith('#') and current_info:
            # Ajouter la chaîne avec son URL
            channels[current_info['key']] = {
                'name': current_info['display_name'],
                'url': line,
                'group': current_info['group']
            }
            current_info = {}

async def load_channels():
    """Charge les chaînes depuis l'URL M3U configurée."""
    if not M3U_URL:
        print("⚠️ Aucune URL M3U configurée")
        return False
    
    try:
        response = requests.get(M3U_URL)
        if response.status_code == 200:
            load_channels_from_m3u(response.text)
            print(f"✅ {len(channels)} chaînes chargées avec succès")
            return True
        else:
            print("❌ Impossible de charger le fichier M3U")
            return False
    except Exception as e:
        print(f"❌ Erreur lors du chargement : {str(e)}")
        return False

@bot.event
async def on_ready():
    """Événement déclenché quand le bot est prêt."""
    print(f"Bot connecté en tant que {bot.user}")
    print(f"Bot prêt à être utilisé sur le serveur autorisé (ID: {ALLOWED_GUILD_ID})")
    
    # Charger les chaînes au démarrage
    await load_channels()

@bot.event
async def on_guild_join(guild):
    """Événement déclenché quand le bot rejoint un serveur."""
    if guild.id != ALLOWED_GUILD_ID:
        await guild.leave()
        print(f"Le bot a quitté un serveur non autorisé : {guild.name}")

@bot.command(name="tv")
@commands.cooldown(1, int(os.getenv("COMMAND_COOLDOWN", 3)), commands.BucketType.user)
async def tv(ctx, action=None, *args):
    """Commande principale pour gérer la TV."""
    if ctx.guild.id != ALLOWED_GUILD_ID:
        return
    
    if not action:
        await ctx.send(
            "```Commandes disponibles:\n"
            "!tv list [groupe] - Affiche la liste des chaînes (optionnellement par groupe)\n"
            "!tv play <chaîne> - Lance une chaîne\n"
            "!tv quit - Arrête la diffusion\n"
            "!tv groups - Affiche les groupes disponibles\n"
            "!tv current - Affiche la chaîne en cours de diffusion```"
        )
        return

    if action.lower() == "list":
        if not channels:
            await ctx.send("❌ Aucune chaîne n'est configurée. Utilisez !tv_refresh pour charger les chaînes.")
            return
        
        # Si un groupe est spécifié
        if args:
            group = " ".join(args).lower()
            filtered_channels = {k: v for k, v in channels.items() if v['group'].lower() == group}
            if not filtered_channels:
                await ctx.send(f"❌ Aucune chaîne trouvée dans le groupe '{group}'")
                return
            channel_list = "\n".join([f"- {info['name']}" for info in filtered_channels.values()])
            await ctx.send(f"**📺 Chaînes du groupe {group}:**\n```{channel_list}```")
        else:
            # Créer une liste paginée des chaînes
            channel_list = "\n".join([f"- {info['name']} ({info['group']})" for info in channels.values()])
            # Si la liste est trop longue, on la divise
            if len(channel_list) > 1900:  # Limite Discord
                parts = [channel_list[i:i+1900] for i in range(0, len(channel_list), 1900)]
                for i, part in enumerate(parts, 1):
                    await ctx.send(f"**📺 Chaînes disponibles (partie {i}/{len(parts)}):**\n```{part}```")
            else:
                await ctx.send(f"**📺 Chaînes disponibles:**\n```{channel_list}```")

    elif action.lower() == "groups":
        if not channels:
            await ctx.send("❌ Aucune chaîne n'est configurée.")
            return
        
        groups = sorted(set(info['group'] for info in channels.values()))
        await ctx.send(f"**📺 Groupes disponibles:**\n```{', '.join(groups)}```")

    elif action.lower() == "current":
        if not current_channel:
            await ctx.send("❌ Aucune chaîne n'est en cours de diffusion.")
            return
        await ctx.send(f"📺 En cours de diffusion : **{channels[current_channel]['name']}** ({channels[current_channel]['group']})")

    elif action.lower() == "play":
        if not args:
            await ctx.send("❌ Veuillez spécifier une chaîne. Utilisez !tv list pour voir les chaînes disponibles.")
            return
        
        channel_name = " ".join(args).lower().replace(' ', '_')
        if channel_name not in channels:
            await ctx.send(f"❌ La chaîne '{channel_name}' n'existe pas. Utilisez !tv list pour voir les chaînes disponibles.")
            return

        if not ctx.author.voice:
            await ctx.send("❌ Vous devez être dans un salon vocal pour utiliser cette commande.")
            return

        try:
            voice_channel = ctx.author.voice.channel
            if ctx.voice_client:
                await ctx.voice_client.disconnect()
            
            vc = await voice_channel.connect()
            vc.play(FFmpegPCMAudio(
                channels[channel_name]['url'],
                options=FFMPEG_OPTIONS
            ))
            global current_channel
            current_channel = channel_name
            await ctx.send(f"📺 Diffusion de **{channels[channel_name]['name']}** ({channels[channel_name]['group']})")
        except Exception as e:
            await ctx.send(f"❌ Une erreur est survenue: {str(e)}")

    elif action.lower() == "quit":
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            global current_channel
            current_channel = None
            await ctx.send("✅ Diffusion arrêtée")
        else:
            await ctx.send("❌ Le bot n'est pas connecté à un salon vocal.")

@bot.command(name="tv_refresh")
@commands.has_permissions(administrator=True)
async def refresh_channels(ctx, m3u_url=None):
    """Rafraîchit la liste des chaînes depuis une URL M3U."""
    if ctx.guild.id != ALLOWED_GUILD_ID:
        return
    
    url_to_use = m3u_url or M3U_URL
    if not url_to_use:
        await ctx.send("❌ Veuillez fournir l'URL du fichier M3U ou la configurer dans le fichier .env")
        return
    
    try:
        async with ctx.typing():
            response = requests.get(url_to_use)
            if response.status_code == 200:
                load_channels_from_m3u(response.text)
                await ctx.send(f"✅ Liste des chaînes mise à jour ! {len(channels)} chaînes chargées.")
            else:
                await ctx.send("❌ Impossible de charger le fichier M3U. Vérifiez l'URL.")
    except Exception as e:
        await ctx.send(f"❌ Erreur lors du chargement : {str(e)}")

@bot.event
async def on_command_error(ctx, error):
    """Gestion globale des erreurs."""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Veuillez attendre {error.retry_after:.1f} secondes avant de réutiliser cette commande.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Vous n'avez pas les permissions nécessaires pour utiliser cette commande.")
    else:
        await ctx.send(f"❌ Une erreur est survenue: {str(error)}")

# Lancer le bot
if __name__ == "__main__":
    bot.run(TOKEN)
