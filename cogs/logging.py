"""
Système de logs centralisé pour Moddy
Envoie les logs importants dans un canal Discord
"""

import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional

from config import COLORS


class LoggingSystem(commands.Cog):
    """Gère les logs du bot dans un canal Discord"""

    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = None  # À définir dans config ou BDD
        self._log_channel = None

    @property
    async def log_channel(self) -> Optional[discord.TextChannel]:
        """Récupère le canal de logs"""
        if self._log_channel:
            return self._log_channel

        if self.log_channel_id:
            self._log_channel = self.bot.get_channel(self.log_channel_id)

        return self._log_channel

    async def log_event(
            self,
            title: str,
            description: str,
            event_type: str = "info",
            fields: Optional[dict] = None,
            footer: Optional[str] = None
    ):
        """
        Enregistre un événement dans le canal de logs

        Args:
            title: Titre de l'événement
            description: Description de l'événement
            event_type: Type d'événement (info, success, warning, error, command)
            fields: Champs supplémentaires
            footer: Footer optionnel
        """
        channel = await self.log_channel
        if not channel:
            return

        # Couleurs selon le type
        color_map = {
            "info": 0x5865F2,  # Bleu
            "success": 0x57F287,  # Vert
            "warning": 0xFEE75C,  # Jaune
            "error": 0xED4245,  # Rouge
            "command": 0xEB459E  # Rose (dev)
        }

        embed = discord.Embed(
            title=title,
            description=description,
            color=color_map.get(event_type, None),
            timestamp=datetime.utcnow()
        )

        if fields:
            for name, value in fields.items():
                embed.add_field(name=name, value=f"`{value}`", inline=True)

        if footer:
            embed.set_footer(text=footer)
        else:
            embed.set_footer(text=f"Type: {event_type}")

        try:
            await channel.send(embed=embed)
        except Exception as e:
            import logging
            logger = logging.getLogger('moddy')
            logger.error(f"Erreur envoi log Discord : {e}")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Log quand le bot rejoint un serveur"""
        await self.log_event(
            title="📥 Nouveau serveur",
            description=f"Moddy a rejoint **{guild.name}**",
            event_type="success",
            fields={
                "ID": guild.id,
                "Membres": guild.member_count,
                "Propriétaire": f"{guild.owner} ({guild.owner_id})" if guild.owner else "Inconnu",
                "Créé le": guild.created_at.strftime("%d/%m/%Y")
            }
        )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Log quand le bot quitte un serveur"""
        await self.log_event(
            title="📤 Serveur quitté",
            description=f"Moddy a quitté **{guild.name}**",
            event_type="warning",
            fields={
                "ID": guild.id,
                "Membres": guild.member_count,
                "Durée": f"{(datetime.utcnow() - guild.me.joined_at).days} jours" if guild.me else "Inconnue"
            }
        )

    async def log_command(self, ctx: commands.Context, command_type: str = "dev"):
        """Log l'utilisation d'une commande"""
        await self.log_event(
            title=f"⚙️ Commande {command_type}",
            description=f"`{ctx.prefix}{ctx.command}`",
            event_type="command",
            fields={
                "Utilisateur": f"{ctx.author} ({ctx.author.id})",
                "Serveur": f"{ctx.guild.name} ({ctx.guild.id})" if ctx.guild else "DM",
                "Canal": f"#{ctx.channel.name}" if hasattr(ctx.channel, 'name') else "DM"
            }
        )

    @commands.command(name="setlogs", hidden=True)
    async def set_log_channel(self, ctx, channel: discord.TextChannel):
        """Définit le canal de logs (commande dev)"""
        if not self.bot.is_developer(ctx.author.id):
            return

        self.log_channel_id = channel.id
        self._log_channel = channel

        # Sauvegarder dans la config ou BDD si nécessaire

        await ctx.send(f"✅ Canal de logs défini : {channel.mention}")
        await self.log_event(
            title="📋 Canal de logs configuré",
            description=f"Les logs seront envoyés dans {channel.mention}",
            event_type="success"
        )


async def setup(bot):
    await bot.add_cog(LoggingSystem(bot))