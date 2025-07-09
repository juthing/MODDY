"""
Commande slash de test pour le système d'erreurs
Permet de vérifier que le tracking fonctionne correctement
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal

from config import COLORS


class TestError(commands.Cog):
    """Commande de test pour le système d'erreurs"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="testerror",
        description="Déclenche une erreur de test pour vérifier le système de tracking"
    )
    @app_commands.describe(
        error_type="Type d'erreur à déclencher",
        private="Rendre la réponse visible uniquement pour toi"
    )
    async def test_error(
            self,
            interaction: discord.Interaction,
            error_type: Literal["division", "index", "key", "attribute", "value", "custom"] = "division",
            private: bool = True
    ):
        """Commande slash pour tester le système d'erreurs"""

        # Embed d'avertissement
        embed = discord.Embed(
            title="Test du système d'erreurs",
            description=f"Je vais déclencher une erreur de type : `{error_type}`\n\n"
                        "Cette erreur est intentionnelle pour tester le système de tracking.",
            color=COLORS["warning"]
        )

        await interaction.response.send_message(embed=embed, ephemeral=private)

        # Déclenche l'erreur selon le type choisi
        try:
            if error_type == "division":
                # Division par zéro
                result = 10 / 0

            elif error_type == "index":
                # Index hors limites
                test_list = [1, 2, 3]
                value = test_list[10]

            elif error_type == "key":
                # Clé inexistante
                test_dict = {"a": 1, "b": 2}
                value = test_dict["z"]

            elif error_type == "attribute":
                # Attribut inexistant
                test_string = "Hello"
                test_string.cette_methode_nexiste_pas()

            elif error_type == "value":
                # ValueError
                number = int("pas_un_nombre")

            elif error_type == "custom":
                # Erreur personnalisée
                raise Exception(f"Erreur de test déclenchée par {interaction.user} dans #{interaction.channel.name}")

        except Exception as e:
            # L'erreur sera automatiquement capturée par le système ErrorTracker
            # On ne fait rien ici car on veut que l'erreur remonte
            raise

    @app_commands.command(
        name="errorinfo",
        description="Affiche des informations sur le système de tracking d'erreurs"
    )
    async def error_info(self, interaction: discord.Interaction):
        """Affiche des infos sur le système d'erreurs"""

        error_tracker = self.bot.get_cog("ErrorTracker")

        if not error_tracker:
            await interaction.response.send_message(
                "Le système de tracking d'erreurs n'est pas chargé.",
                ephemeral=True
            )
            return

        # Compte les erreurs
        error_count = len(error_tracker.error_cache)

        embed = discord.Embed(
            title="Système de tracking d'erreurs",
            description=(
                "Le système de tracking d'erreurs est opérationnel.\n\n"
                "**Comment ça marche :**\n"
                "• Les erreurs génèrent un code unique\n"
                "• Les détails sont envoyés dans un canal dédié\n"
                "• Les erreurs fatales ping le développeur\n"
                "• Tu peux partager le code d'erreur pour assistance"
            ),
            color=COLORS["info"]
        )

        embed.add_field(
            name="Statistiques",
            value=f"**Erreurs en cache :** `{error_count}/100`\n"
                  f"**Canal de logs :** <#{error_tracker.error_channel_id}>",
            inline=False
        )

        embed.add_field(
            name="Tester le système",
            value="Utilise `/testerror` pour déclencher une erreur de test",
            inline=False
        )

        embed.set_footer(text="Les erreurs normales (permissions, cooldown) ne sont pas trackées")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(TestError(bot))