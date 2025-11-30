"""
Commande ping publique avec Components V2
"""
import asyncio
import time
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import LayoutView, Container, TextDisplay, Separator
from discord import SeparatorSpacing

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
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(
        incognito="Make response visible only to you"
    )
    async def ping_slash(self, interaction: discord.Interaction, incognito: Optional[bool] = None):
        """Commande slash /ping avec i18n automatique et Components V2"""

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
            emoji = "⚠️"
        else:
            status_key = "poor"
            emoji = EMOJIS["undone"]

        # Récupérer le texte du statut traduit
        status = t(f"commands.ping.status.{status_key}", interaction)

        # Créer le message initial avec Components V2
        view = LayoutView()
        container = Container()

        # Header avec titre
        title = t("commands.ping.response.title", interaction)
        header = f"{emoji} **{title}**"
        container.add_item(TextDisplay(header))

        # Separator
        container.add_item(Separator(spacing=SeparatorSpacing.small))

        # Description avec statut
        description = t(
            "commands.ping.response.description",
            interaction,
            emoji=emoji,
            status=status,
            api_latency=api_latency,
            message_latency=t("common.loading", interaction)
        )
        container.add_item(TextDisplay(description))

        # Footer
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        footer = t(
            "commands.ping.response.footer",
            interaction,
            guild_count=len(self.bot.guilds)
        )
        container.add_item(TextDisplay(f"*{footer}*"))

        view.add_item(container)

        # Envoyer le message initial
        await interaction.response.send_message(view=view, ephemeral=ephemeral)

        # Calculer la latence du message
        end = time.perf_counter()
        message_latency = round((end - start) * 1000)

        # Créer le message mis à jour avec la latence réelle
        view_updated = LayoutView()
        container_updated = Container()

        # Header
        container_updated.add_item(TextDisplay(header))
        container_updated.add_item(Separator(spacing=SeparatorSpacing.small))

        # Description avec latence mise à jour
        description_updated = t(
            "commands.ping.response.description",
            interaction,
            emoji=emoji,
            status=status,
            api_latency=api_latency,
            message_latency=f"`{message_latency}ms`"
        )
        container_updated.add_item(TextDisplay(description_updated))

        # Footer
        container_updated.add_item(Separator(spacing=SeparatorSpacing.small))
        container_updated.add_item(TextDisplay(f"*{footer}*"))

        view_updated.add_item(container_updated)

        # Modifier le message avec la latence réelle
        await interaction.edit_original_response(view=view_updated)


async def setup(bot):
    await bot.add_cog(PublicPing(bot))