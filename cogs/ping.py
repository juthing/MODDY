"""
Commande ping publique 
"""
import asyncio
import time
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import COLORS, EMOJIS
from utils.i18n import i18n, t


class PublicPing(commands.Cog):
    """Commande ping pour tous les utilisateurs"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Check the bot's latency"
    )
    @app_commands.describe(
        incognito="Make response visible only to you"
    )
    async def ping_slash(self, interaction: discord.Interaction, incognito: Optional[bool] = None):
        """Commande slash /ping avec i18n automatique"""

        # === BLOC INCOGNITO ===
        if incognito is None and self.bot.db:
            try:
                user_pref = await self.bot.db.get_attribute('user', interaction.user.id, 'DEFAULT_INCOGNITO')
                ephemeral = True if user_pref is None else user_pref
            except:
                ephemeral = True
        else:
            ephemeral = incognito if incognito is not None else True

        # Mesure du temps de début
        start = time.perf_counter()

        # Latence API
        api_latency = round(self.bot.latency * 1000)

        # Déterminer la qualité de la connexion et l'emoji
        if api_latency < 50:
            status_key = "excellent"
            emoji = EMOJIS["done"]
        elif api_latency < 100:
            status_key = "good"
            emoji = EMOJIS["info"]
        elif api_latency < 200:
            status_key = "average"
            emoji = EMOJIS["warning"]
        else:
            status_key = "poor"
            emoji = EMOJIS["error"]

        # Récupérer le texte du statut traduit
        status = t(f"commands.ping.status.{status_key}", interaction)

        # Créer l'embed initial avec le chargement
        embed = discord.Embed(
            title=t("commands.ping.response.title", interaction),
            description=t(
                "commands.ping.response.description",
                interaction,
                emoji=emoji,
                status=status,
                api_latency=api_latency,
                message_latency=t("common.loading", interaction)
            ),
            color=COLORS["primary"],
            timestamp=datetime.utcnow()
        )

        embed.set_footer(
            text=t(
                "commands.ping.response.footer",
                interaction,
                guild_count=len(self.bot.guilds)
            ),
            icon_url=self.bot.user.display_avatar.url if self.bot.user else None
        )

        # Envoyer le message initial
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

        # Calculer la latence du message
        end = time.perf_counter()
        message_latency = round((end - start) * 1000)

        # Mettre à jour l'embed avec la latence réelle
        embed.description = t(
            "commands.ping.response.description",
            interaction,
            emoji=emoji,
            status=status,
            api_latency=api_latency,
            message_latency=f"`{message_latency}ms`"
        )

        # Modifier le message avec l'embed final
        await interaction.edit_original_response(embed=embed)


async def setup(bot):
    await bot.add_cog(PublicPing(bot))