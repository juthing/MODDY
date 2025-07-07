"""
Commande reboot pour développeurs
Redémarre le bot et modifie le message original
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

from config import COLORS, EMOJIS


class Reboot(commands.Cog):
    """Commande pour redémarrer le bot"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="reboot", aliases=["restart", "reload"])
    async def reboot(self, ctx):
        """Redémarre le bot automatiquement"""

        # Embed initial
        embed = discord.Embed(
            title=f"{EMOJIS['loading']} Redémarrage en cours...",
            description="Le bot va redémarrer dans quelques secondes.",
            color=COLORS["warning"],
            timestamp=datetime.utcnow()
        )
        embed.set_footer(
            text=f"Demandé par {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )

        # Envoyer le message
        msg = await ctx.send(embed=embed)

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

            # Créer le nouvel embed
            embed = discord.Embed(
                title=f"{EMOJIS['success']} Redémarrage terminé !",
                color=COLORS["success"],
                timestamp=datetime.utcnow()
            )

            # Description stylée
            if reboot_duration < 5:
                speed = "⚡ Ultra rapide"
            elif reboot_duration < 10:
                speed = "🚀 Rapide"
            elif reboot_duration < 20:
                speed = "✨ Normal"
            else:
                speed = "🐌 Lent"

            embed.description = (
                f"{speed} - **{reboot_duration:.1f}** secondes\n\n"
                f"```ansi\n"
                f"\u001b[2;32m✓ Connexion Discord\u001b[0m\n"
                f"\u001b[2;32m✓ Chargement des modules\u001b[0m\n"
                f"\u001b[2;32m✓ Base de données\u001b[0m\n"
                f"\u001b[2;32m✓ Commandes synchronisées\u001b[0m\n"
                f"```"
            )

            # Stats
            embed.add_field(
                name="📊 Statistiques",
                value=f"**Serveurs:** {len(self.bot.guilds)}\n"
                      f"**Utilisateurs:** {len(self.bot.users)}\n"
                      f"**Latence:** {round(self.bot.latency * 1000)}ms",
                inline=True
            )

            embed.add_field(
                name="🔧 Système",
                value=f"**Commandes:** {len(self.bot.commands)}\n"
                      f"**Cogs:** {len(self.bot.cogs)}\n"
                      f"**Version:** discord.py {discord.__version__}",
                inline=True
            )

            # Footer avec les infos originales
            embed.set_footer(
                text=f"Demandé par {info['author_name']}",
                icon_url=info["author_avatar"]
            )

            # Mettre à jour le message
            await message.edit(embed=embed)

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