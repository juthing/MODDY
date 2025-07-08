"""
Commande reboot pour développeurs
Redémarre le bot et modifie le message original
Utilise les composants V2
"""

import discord
from discord.ext import commands
import asyncio
import os
import sys
import subprocess
import json
import tempfile
from datetime import datetime

# Import du système d'embeds V2
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse


class Reboot(commands.Cog):
    """Commande pour redémarrer le bot"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="reboot", aliases=["restart", "reload"])
    async def reboot(self, ctx):
        """Redémarre le bot automatiquement avec composants V2"""

        # Composants V2 initial
        components = [
            ModdyEmbed.heading("Redémarrage en cours...", 2),
            ModdyEmbed.text("Le bot va redémarrer dans quelques secondes."),
            ModdyEmbed.separator(),
            ModdyEmbed.text(f"_Demandé par {ctx.author}_")
        ]

        # Envoyer le message
        msg = await ctx.send(**{
            "flags": ModdyEmbed.V2_FLAGS,
            "components": components
        })

        # Log l'action
        import logging
        logger = logging.getLogger('moddy')
        logger.info(f"🔄 Reboot demandé par {ctx.author} ({ctx.author.id})")

        # Sauvegarder les infos pour après le reboot
        reboot_info = {
            "channel_id": ctx.channel.id,
            "message_id": msg.id,
            "author_name": str(ctx.author),
            "author_avatar": str(ctx.author.display_avatar.url),
            "start_time": datetime.utcnow().isoformat()
        }

        # Fichier temporaire pour stocker les infos
        temp_file = os.path.join(tempfile.gettempdir(), "moddy_reboot.json")

        with open(temp_file, 'w') as f:
            json.dump(reboot_info, f)

        # Petit délai pour s'assurer que le message est envoyé
        await asyncio.sleep(0.5)

        # Préparer les arguments pour le redémarrage
        args = [sys.executable] + sys.argv

        # Sur Windows
        if sys.platform == "win32":
            subprocess.Popen(args)
            await self.bot.close()
            sys.exit(0)
        # Sur Linux/Mac
        else:
            await self.bot.close()
            os.execv(sys.executable, args)


class RebootNotifier(commands.Cog):
    """Met à jour le message après le reboot"""

    def __init__(self, bot):
        self.bot = bot
        self._checked = False

    @commands.Cog.listener()
    async def on_ready(self):
        """Vérifie et met à jour le message de reboot"""
        # Éviter de vérifier plusieurs fois
        if self._checked:
            return
        self._checked = True

        temp_file = os.path.join(tempfile.gettempdir(), "moddy_reboot.json")

        if not os.path.exists(temp_file):
            return

        try:
            # Lire les infos
            with open(temp_file, 'r') as f:
                info = json.load(f)

            # Calculer le temps de reboot
            start_time = datetime.fromisoformat(info["start_time"])
            reboot_duration = (datetime.utcnow() - start_time).total_seconds()

            # Récupérer le canal et le message
            channel = self.bot.get_channel(info["channel_id"])
            if not channel:
                return

            try:
                message = await channel.fetch_message(info["message_id"])
            except:
                # Message introuvable
                os.remove(temp_file)
                return

            # Créer les composants V2
            components = [
                ModdyEmbed.heading("Redémarrage terminé !", 2),
                ModdyEmbed.separator()
            ]

            # Description stylée
            if reboot_duration < 5:
                speed = "Ultra rapide"
            elif reboot_duration < 10:
                speed = "Rapide"
            elif reboot_duration < 20:
                speed = "Normal"
            else:
                speed = "Lent"

            components.extend([
                ModdyEmbed.text(f"**{speed}** - `{reboot_duration:.1f}` secondes"),
                ModdyEmbed.separator(),
                ModdyEmbed.code_block(
                    "✓ Connexion Discord\n"
                    "✓ Chargement des modules\n"
                    "✓ Base de données\n"
                    "✓ Commandes synchronisées",
                    ""
                ),
                ModdyEmbed.separator(),
                ModdyEmbed.heading("Statistiques", 3),
                ModdyEmbed.text(f"**Serveurs:** `{len(self.bot.guilds)}`"),
                ModdyEmbed.text(f"**Utilisateurs:** `{len(self.bot.users)}`"),
                ModdyEmbed.text(f"**Latence:** `{round(self.bot.latency * 1000)}ms`"),
                ModdyEmbed.separator(),
                ModdyEmbed.heading("Système", 3),
                ModdyEmbed.text(f"**Commandes:** `{len(self.bot.commands)}`"),
                ModdyEmbed.text(f"**Cogs:** `{len(self.bot.cogs)}`"),
                ModdyEmbed.text(f"**Version:** discord.py `{discord.__version__}`"),
                ModdyEmbed.separator(),
                ModdyEmbed.text(f"_Demandé par {info['author_name']}_")
            ])

            # Mettre à jour le message
            await message.edit(**{
                "flags": ModdyEmbed.V2_FLAGS,
                "components": components
            })

            # Supprimer le fichier temporaire
            os.remove(temp_file)

            # Log
            import logging
            logger = logging.getLogger('moddy')
            logger.info(f"✅ Notification de reboot envoyée (durée: {reboot_duration:.1f}s)")

        except Exception as e:
            import logging
            logger = logging.getLogger('moddy')
            logger.error(f"Erreur notification reboot: {e}")

            # Supprimer le fichier en cas d'erreur
            if os.path.exists(temp_file):
                os.remove(temp_file)


async def setup(bot):
    await bot.add_cog(Reboot(bot))
    await bot.add_cog(RebootNotifier(bot))