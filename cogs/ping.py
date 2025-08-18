"""
Commande ping publique
Simple et accessible à tous
"""

import nextcord
from nextcord import app_commands
from nextcord.ext import commands
import time
from datetime import datetime
from typing import Optional

from config import COLORS, EMOJIS


class PublicPing(commands.Cog):
    """Commande ping pour tous les utilisateurs"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Vérifie la latence du bot / Checks the bot's latency")
    @app_commands.describe(
        incognito="Rendre la réponse visible uniquement pour vous / Make response visible only to you"
    )
    async def ping_slash(self, interaction: nextcord.Interaction, incognito: Optional[bool] = None):
        """Commande slash /ping simple pour tout le monde"""

        # === BLOC INCOGNITO ===
        ephemeral = True
        if incognito is None and self.bot.db:
            try:
                user_pref = await self.bot.db.get_attribute('user', interaction.user.id, 'DEFAULT_INCOGNITO')
                if user_pref is not None:
                    ephemeral = user_pref
            except Exception:
                # En cas d'erreur, on garde la valeur par défaut (privé)
                pass
        elif incognito is not None:
            ephemeral = incognito
        # === FIN DU BLOC INCOGNITO ===

        # Calcul des latences
        start = time.perf_counter()

        # Latence API
        api_latency = round(self.bot.latency * 1000)

        # Déterminer la qualité de la connexion
        if api_latency < 100:
            status = "Bonne"
            emoji = EMOJIS.get('done', '✅')
        elif api_latency < 200:
            status = "Moyenne"
            emoji = EMOJIS.get('undone', '❌')
        else:
            status = "Mauvaise"
            emoji = EMOJIS.get('undone', '❌')

        # Créer l'embed avec du contenu
        embed = nextcord.Embed(
            title=f"{EMOJIS.get('ping', '🏓')} Pong!",
            description=(
                f"{emoji} **Connexion {status}**\n\n"
                f"**Latence API Discord:** `{api_latency}ms`\n"
                f"**Temps de réponse:** `Calcul en cours...`"
            ),
            color=COLORS["primary"],
            timestamp=datetime.utcnow()
        )

        # Footer avec le nombre de serveurs
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