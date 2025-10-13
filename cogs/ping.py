"""
Commande ping publique
Simple et accessible à tous
"""
import asyncio
import time
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from config import COLORS, EMOJIS


class PublicPing(commands.Cog):
    """Commande ping pour tous les utilisateurs"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Vérifie la latence du bot / Check the bot's latency")
    @app_commands.describe(
        incognito="Rendre la réponse visible uniquement pour vous / Make response visible only to you"
    )
    async def ping_slash(self, interaction: discord.Interaction, incognito: Optional[bool] = None):
        """Commande slash /ping simple pour tout le monde"""

        # === BLOC INCOGNITO - À copier au début de chaque commande ===
        if incognito is None and self.bot.db:
            try:
                user_pref = await self.bot.db.get_attribute('user', interaction.user.id, 'DEFAULT_INCOGNITO')
                ephemeral = True if user_pref is None else user_pref
            except:
                ephemeral = True
        else:
            ephemeral = incognito if incognito is not None else True
        # === FIN DU BLOC INCOGNITO ===

        # === GESTION BUG "Interaction already acknowledged" ===
        await asyncio.sleep(0.1)
        if interaction.response.is_done():
            # The language manager has already responded. We must use a followup.
            # This means we cannot measure message latency. We'll only show API latency.
            api_latency = round(self.bot.latency * 1000)

            if api_latency < 50:
                status = "Excellente"
                emoji = EMOJIS["done"]
            elif api_latency < 100:
                status = "Bonne"
                emoji = EMOJIS["info"]
            elif api_latency < 200:
                status = "Moyenne"
                emoji = EMOJIS["warning"]
            else:
                status = "Mauvaise"
                emoji = EMOJIS["error"]

            embed = discord.Embed(
                title=f"{EMOJIS['ping']} Pong!",
                description=(
                    f"{emoji} **Connexion {status}**\n\n"
                    f"**Latence API Discord:** `{api_latency}ms`"
                ),
                color=COLORS["primary"],
                timestamp=datetime.utcnow()
            )
            embed.set_footer(
                text=f"Moddy • {len(self.bot.guilds)} serveurs",
                icon_url=self.bot.user.display_avatar.url if self.bot.user else None
            )
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)
            return

        # === Normal execution flow ===
        start = time.perf_counter()

        # Latence API
        api_latency = round(self.bot.latency * 1000)

        # Déterminer la qualité de la connexion
        if api_latency < 50:
            status = "Excellente"
            emoji = EMOJIS["done"]
        elif api_latency < 100:
            status = "Bonne"
            emoji = EMOJIS["info"]
        elif api_latency < 200:
            status = "Moyenne"
            emoji = EMOJIS["warning"]
        else:
            status = "Mauvaise"
            emoji = EMOJIS["error"]

        # Créer l'embed avec du contenu
        embed = discord.Embed(
            title=f"{EMOJIS['ping']} Pong!",
            description=(
                f"{emoji} **Connexion {status}**\n\n"
                f"**Latence API Discord:** `{api_latency}ms`\n"
                f"**Temps de réponse:** {EMOJIS['loading']}"
            ),
            color=COLORS["primary"],
            timestamp=datetime.utcnow()
        )

        embed.set_footer(
            text=f"Moddy • {len(self.bot.guilds)} serveurs",
            icon_url=self.bot.user.display_avatar.url if self.bot.user else None
        )

        # Envoyer le message
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
        end = time.perf_counter()
        message_latency = round((end - start) * 1000)

        # Mettre à jour avec la latence du message
        embed.description = (
            f"{emoji} **Connexion {status}**\n\n"
            f"**Latence API Discord:** `{api_latency}ms`\n"
            f"**Temps de réponse:** `{message_latency}ms`"
        )

        # Modifier le message avec l'embed final
        await interaction.edit_original_response(embed=embed)


async def setup(bot):
    await bot.add_cog(PublicPing(bot))