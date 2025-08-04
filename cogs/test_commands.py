"""
Commande slash test pour Moddy
Démontre différents types d'interactions et utilise le système d'embeds épuré
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from typing import Optional

from utils.embeds import ModdyEmbed, ModdyResponse, ModdyColors
from config import COLORS


class TestCommands(commands.Cog):
    """Commandes de test pour démontrer les fonctionnalités"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="test", description="Commande de test avec différentes options")
    @app_commands.describe(
        message="Message à afficher",
        nombre="Un nombre pour tester",
        choix="Choix dans une liste",
        utilisateur="Utilisateur à mentionner",
        ephemeral="Message visible seulement par toi"
    )
    @app_commands.choices(choix=[
        app_commands.Choice(name="Option 1", value="option1"),
        app_commands.Choice(name="Option 2", value="option2"),
        app_commands.Choice(name="Option 3", value="option3")
    ])
    async def test_command(
            self,
            interaction: discord.Interaction,
            message: str = "Test par défaut",
            nombre: Optional[int] = None,
            choix: Optional[app_commands.Choice[str]] = None,
            utilisateur: Optional[discord.Member] = None,
            ephemeral: bool = False
    ):
        """Commande de test principale"""

        # Embed principal avec les infos
        embed = ModdyEmbed.create(
            title="<:done:1398729525277229066> Commande Test",
            description=f"**Message :** {message}",
            color=COLORS["success"],
            timestamp=True
        )

        # Ajoute les champs selon les paramètres fournis
        fields = []

        if nombre is not None:
            fields.append(("Nombre fourni", f"`{nombre}`", True))
            fields.append(("Nombre x2", f"`{nombre * 2}`", True))

        if choix:
            fields.append(("Choix sélectionné", f"`{choix.name}` (valeur: `{choix.value}`)", True))

        if utilisateur:
            fields.append(("Utilisateur", f"{utilisateur.mention}", True))
            fields.append(("ID Utilisateur", f"`{utilisateur.id}`", True))

        # Infos sur l'interaction
        fields.append(("Serveur", interaction.guild.name if interaction.guild else "DM", True))
        fields.append(("Canal", f"<#{interaction.channel.id}>", True))
        fields.append(("Ephémère", "Oui" if ephemeral else "Non", True))

        # Ajoute les champs à l'embed
        if fields:
            for field in fields:
                embed.add_field(name=field[0], value=field[1], inline=field[2])

        # Footer avec l'auteur
        embed.set_footer(
            text=f"Testé par {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )

        # Vue avec boutons pour plus d'interactions
        view = TestView(self.bot, interaction.user)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)

    @app_commands.command(name="testdb", description="Test de la base de données (dev uniquement)")
    async def test_database(self, interaction: discord.Interaction):
        """Test de la base de données"""

        # Vérifie si c'est un développeur
        if not self.bot.is_developer(interaction.user.id):
            embed = ModdyResponse.error(
                "Accès refusé",
                "Cette commande est réservée aux développeurs."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Vérifie la connexion BDD
        if not self.bot.db:
            embed = ModdyResponse.error(
                "Base de données indisponible",
                "La base de données n'est pas connectée."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Message de chargement
        embed = ModdyResponse.loading("Test de la base de données en cours...")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            # Test simple : récupère l'utilisateur
            user_data = await self.bot.db.get_user(interaction.user.id)

            # Test des statistiques
            stats = await self.bot.db.get_stats()

            # Embed de résultat
            result_embed = ModdyEmbed.create(
                title="<:done:1398729525277229066> Test BDD réussi",
                description="La base de données fonctionne correctement",
                color=COLORS["success"]
            )

            # Infos utilisateur
            result_embed.add_field(
                name="<:user:1398729712204779571> Tes données",
                value=(
                    f"**Attributs :** `{len(user_data['attributes'])}`\n"
                    f"**Données :** {'Oui' if user_data['data'] else 'Non'}"
                ),
                inline=True
            )

            # Stats générales
            result_embed.add_field(
                name="<:info:1401614681440784477> Statistiques",
                value=(
                    f"**Utilisateurs :** `{stats.get('users', 0)}`\n"
                    f"**Serveurs :** `{stats.get('guilds', 0)}`\n"
                    f"**Erreurs :** `{stats.get('errors', 0)}`"
                ),
                inline=True
            )

            await interaction.edit_original_response(embed=result_embed)

        except Exception as e:
            error_embed = ModdyResponse.error(
                "Erreur de test",
                f"Une erreur s'est produite : `{str(e)}`"
            )
            await interaction.edit_original_response(embed=error_embed)

    @app_commands.command(name="testping", description="Test de latence simple")
    async def test_ping(self, interaction: discord.Interaction):
        """Test de ping simple"""

        import time
        start = time.perf_counter()

        # Détermine la qualité de la connexion
        api_latency = round(self.bot.latency * 1000)

        if api_latency < 50:
            status = "Excellente"
            color = COLORS["success"]
        elif api_latency < 100:
            status = "Bonne"
            color = COLORS["primary"]
        elif api_latency < 200:
            status = "Moyenne"
            color = COLORS["warning"]
        else:
            status = "Mauvaise"
            color = COLORS["error"]

        embed = ModdyEmbed.create(
            title="<:sync:1398729150885269546> Test de Ping",
            description=f"**Connexion {status}**",
            color=color
        )

        embed.add_field(
            name="Latence API Discord",
            value=f"`{api_latency}ms`",
            inline=True
        )

        embed.add_field(
            name="Temps de réponse",
            value="`Calcul...`",
            inline=True
        )

        # Envoie d'abord la réponse
        await interaction.response.send_message(embed=embed)

        # Calcule le temps de réponse
        end = time.perf_counter()
        response_time = round((end - start) * 1000)

        # Met à jour l'embed
        embed.set_field_at(
            1,
            name="Temps de réponse",
            value=f"`{response_time}ms`",
            inline=True
        )

        embed.set_footer(text=f"Testé par {interaction.user}")

        await interaction.edit_original_response(embed=embed)


class TestView(discord.ui.View):
    """Vue avec boutons de test"""

    def __init__(self, bot, user):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.clicks = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Seul l'utilisateur initial peut utiliser les boutons"""
        if interaction.user != self.user:
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Seul l'auteur de la commande peut utiliser ces boutons.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Cliquer ici", emoji="<:done:1398729525277229066>", style=discord.ButtonStyle.primary)
    async def click_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Bouton de test"""
        self.clicks += 1

        # Change le style du bouton selon le nombre de clics
        if self.clicks < 3:
            button.style = discord.ButtonStyle.success
        elif self.clicks < 5:
            button.style = discord.ButtonStyle.warning
        else:
            button.style = discord.ButtonStyle.danger
            button.label = "Arrête !"

        button.label = f"Cliqué {self.clicks} fois"

        embed = ModdyEmbed.create(
            title="<:loading:1395047662092550194> Bouton cliqué !",
            description=f"Tu as cliqué **{self.clicks}** fois sur ce bouton.",
            color=COLORS["info"]
        )

        if self.clicks >= 10:
            embed.title = "<:undone:1398729502028333218> Vraiment ?"
            embed.description = f"Bon ok, tu as cliqué **{self.clicks}** fois. Je pense que ça suffit maintenant."
            embed.color = COLORS["error"]

            # Désactive le bouton
            button.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Réinitialiser", emoji="<:sync:1398729150885269546>", style=discord.ButtonStyle.secondary)
    async def reset_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remet le compteur à zéro"""
        self.clicks = 0

        # Remet le premier bouton à l'état initial
        click_btn = self.children[0]
        click_btn.label = "Cliquer ici"
        click_btn.style = discord.ButtonStyle.primary
        click_btn.disabled = False

        embed = ModdyEmbed.create(
            title="<:sync:1398729150885269546> Remise à zéro",
            description="Le compteur a été remis à zéro !",
            color=COLORS["success"]
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Fermer", emoji="<:undone:1398729502028333218>", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ferme la vue"""
        embed = ModdyEmbed.create(
            title="Test terminé",
            description="Le test a été fermé.",
            color=COLORS["info"]
        )

        # Désactive tous les boutons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        """Appelé quand la vue expire"""
        # Désactive tous les boutons
        for item in self.children:
            item.disabled = True


async def setup(bot):
    await bot.add_cog(TestCommands(bot))