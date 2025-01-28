# Bot Discord IPTV

Ce bot permet de diffuser des chaînes IPTV dans un salon vocal Discord.

## Prérequis

- Python 3.8 ou supérieur
- FFmpeg installé sur le système
- Un token de bot Discord
- Un serveur Discord où vous avez les permissions administrateur

## Installation

1. Installez les dépendances :
```bash
pip install -r requirements.txt
```

2. Installez FFmpeg :
- Windows : Téléchargez FFmpeg depuis [le site officiel](https://ffmpeg.org/download.html)
- Linux : `sudo apt install ffmpeg`

3. Configurez le fichier `.env` :
```env
DISCORD_TOKEN=votre_token_discord
GUILD_ID=id_de_votre_serveur
```

## Configuration des chaînes

Modifiez la variable `channels` dans `bot.py` pour ajouter vos chaînes IPTV :

```python
channels = {
    "nom_chaine": "url_du_flux",
    "france2": "http://exemple.com/france2.m3u8",
}
```

## Commandes disponibles

- `!tv` : Affiche l'aide
- `!tv list` : Affiche la liste des chaînes disponibles
- `!tv play <chaîne>` : Lance la diffusion d'une chaîne
- `!tv quit` : Arrête la diffusion

## Sécurité

Le bot est configuré pour fonctionner uniquement sur le serveur Discord spécifié dans le fichier `.env`. Il quittera automatiquement tout autre serveur.
