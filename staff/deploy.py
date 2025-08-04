"""
Commande deploy pour développeurs
Permet de mettre à jour le bot depuis GitHub directement sur le VPS
Version pour repository public
"""

import discord
from discord.ext import commands
import subprocess
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse, ModdyColors
from config import COLORS


class Deploy(commands.Cog):
    """Commande pour déployer les mises à jour depuis GitHub"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="deploy", aliases=["update", "pull", "git"])
    async def deploy(self, ctx, branch: str = None):
        """Déploie les dernières modifications depuis GitHub"""

        # Vérifie d'abord s'il y a des changements
        checking_embed = discord.Embed(
            title="<:sync:1398729150885269546> Vérification des mises à jour...",
            description="Recherche de modifications sur GitHub",
            color=COLORS["info"],
            timestamp=datetime.utcnow()
        )
        checking_msg = await ctx.send(embed=checking_embed)

        try:
            # Git fetch pour voir s'il y a des changements
            fetch_result = subprocess.run(
                ["git", "fetch"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )

            if fetch_result.returncode != 0:
                error_embed = ModdyResponse.error(
                    "Erreur Git Fetch",
                    f"```\n{fetch_result.stderr}\n```"
                )
                await checking_msg.edit(embed=error_embed)
                return

            # Obtient la branche actuelle
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            current_branch = branch_result.stdout.strip()

            # Vérifie les commits en avance
            behind_result = subprocess.run(
                ["git", "rev-list", "--count", f"HEAD..origin/{current_branch}"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            commits_behind = int(behind_result.stdout.strip() or "0")

            if commits_behind == 0:
                up_to_date_embed = discord.Embed(
                    title="<:done:1398729525277229066> Déjà à jour",
                    description=f"Le bot est déjà à jour avec la branche `{current_branch}`",
                    color=COLORS["success"]
                )
                await checking_msg.edit(embed=up_to_date_embed)
                return

            # Obtient la liste des changements
            log_result = subprocess.run(
                ["git", "log", f"HEAD..origin/{current_branch}", "--oneline", "--max-count=10"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )

            # Embed de confirmation
            confirm_embed = discord.Embed(
                title="<:commit:1398728993284296806> Déploiement disponible",
                description=(
                    f"**Branche :** `{current_branch}`\n"
                    f"**Commits en retard :** `{commits_behind}`\n\n"
                    "**Changements à déployer :**"
                ),
                color=COLORS["warning"],
                timestamp=datetime.utcnow()
            )

            # Ajoute les commits
            if log_result.stdout:
                commits_preview = log_result.stdout.strip()
                if len(commits_preview) > 1000:
                    commits_preview = commits_preview[:997] + "..."
                confirm_embed.add_field(
                    name="<:commit:1398728993284296806> Commits récents",
                    value=f"```\n{commits_preview}\n```",
                    inline=False
                )

            confirm_embed.set_footer(
                text=f"Demandé par {ctx.author}",
                icon_url=ctx.author.display_avatar.url
            )

            # Vue de confirmation
            view = DeployConfirmView(self.bot, ctx.author, current_branch, commits_behind, checking_msg)

            await checking_msg.edit(embed=confirm_embed, view=view)

        except Exception as e:
            error_embed = ModdyResponse.error(
                "Erreur",
                f"Impossible de vérifier les mises à jour : {str(e)}"
            )
            await checking_msg.edit(embed=error_embed)

            # Log l'erreur
            import logging
            logger = logging.getLogger('moddy')
            logger.error(f"Erreur déploiement : {e}", exc_info=True)


class DeployConfirmView(discord.ui.View):
    """Vue pour confirmer le déploiement"""

    def __init__(self, bot, author, branch, commits_count, message):
        super().__init__(timeout=60)
        self.bot = bot
        self.author = author
        self.branch = branch
        self.commits_count = commits_count
        self.message = message
        self.confirmed = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Seul l'auteur peut utiliser les boutons"""
        if interaction.user != self.author:
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Seul l'auteur de la commande peut confirmer le déploiement.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Déployer", emoji="<:sync:1398729150885269546>", style=discord.ButtonStyle.success)
    async def confirm_deploy(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirme et lance le déploiement"""
        self.confirmed = True

        # Désactive tous les boutons
        for item in self.children:
            item.disabled = True

        # Embed de déploiement en cours
        deploy_embed = discord.Embed(
            title="<:loading:1395047662092550194> Déploiement en cours...",
            description="Récupération des modifications depuis GitHub",
            color=COLORS["info"],
            timestamp=datetime.utcnow()
        )

        await interaction.response.edit_message(embed=deploy_embed, view=self)

        try:
            # Git pull simple (pas besoin d'auth pour un repo public)
            pull_result = subprocess.run(
                ["git", "pull", "origin", self.branch],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )

            if pull_result.returncode == 0:
                # Succès - Analyse les changements
                output_lines = pull_result.stdout.strip().split('\n')

                # Cherche les stats de changements
                files_changed = 0
                insertions = 0
                deletions = 0

                for line in output_lines:
                    if "files changed" in line or "file changed" in line:
                        parts = line.split(',')
                        for part in parts:
                            if "file" in part:
                                files_changed = int(''.join(filter(str.isdigit, part.split('file')[0])) or 0)
                            elif "insertion" in part:
                                insertions = int(''.join(filter(str.isdigit, part.split('insertion')[0])) or 0)
                            elif "deletion" in part:
                                deletions = int(''.join(filter(str.isdigit, part.split('deletion')[0])) or 0)

                # Obtient le dernier commit
                commit_result = subprocess.run(
                    ["git", "log", "-1", "--oneline"],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent.parent
                )
                last_commit = commit_result.stdout.strip()

                # Embed de succès
                success_embed = discord.Embed(
                    title="<:done:1398729525277229066> Déploiement réussi !",
                    description=(
                        f"Les modifications ont été récupérées depuis GitHub.\n\n"
                        f"**Dernier commit :** `{last_commit}`"
                    ),
                    color=COLORS["success"],
                    timestamp=datetime.utcnow()
                )

                # Stats si disponibles
                if files_changed > 0:
                    success_embed.add_field(
                        name="<:commit:1398728993284296806> Changements",
                        value=(
                            f"**Fichiers modifiés :** `{files_changed}`\n"
                            f"**Lignes ajoutées :** `+{insertions}`\n"
                            f"**Lignes supprimées :** `-{deletions}`"
                        ),
                        inline=True
                    )

                success_embed.add_field(
                    name="<:settings:1398729549323440208> Prochaine étape",
                    value=(
                        "1. Va sur ton dashboard Hostinger\n"
                        "2. Redémarre le VPS\n"
                        "3. Le bot sera mis à jour !"
                    ),
                    inline=False
                )

                success_embed.set_footer(
                    text=f"Déployé par {self.author}",
                    icon_url=self.author.display_avatar.url
                )

                await self.message.edit(embed=success_embed, view=self)

                # Log l'action
                if log_cog := self.bot.get_cog("LoggingSystem"):
                    await log_cog.log_command(
                        type('obj', (object,), {
                            'author': self.author,
                            'guild': None,
                            'channel': self.message.channel
                        })(),
                        "deploy",
                        {
                            "branch": self.branch,
                            "commits": self.commits_count,
                            "files_changed": files_changed,
                            "status": "success"
                        }
                    )

            else:
                # Erreur pendant le pull
                error_embed = discord.Embed(
                    title="<:undone:1398729502028333218> Erreur de déploiement",
                    description="Le déploiement a échoué.",
                    color=COLORS["error"],
                    timestamp=datetime.utcnow()
                )

                error_output = pull_result.stderr or pull_result.stdout
                if len(error_output) > 1000:
                    error_output = error_output[:997] + "..."

                error_embed.add_field(
                    name="Détails de l'erreur",
                    value=f"```\n{error_output}\n```",
                    inline=False
                )

                error_embed.add_field(
                    name="<:bug:1401614189482475551> Solutions possibles",
                    value=(
                        "• Vérifie qu'il n'y a pas de conflits locaux\n"
                        "• Assure-toi que la branche existe\n"
                        "• Connecte-toi au VPS pour résoudre manuellement"
                    ),
                    inline=False
                )

                await self.message.edit(embed=error_embed, view=self)

        except Exception as e:
            # Erreur Python
            error_embed = ModdyResponse.error(
                "Erreur système",
                f"Une erreur s'est produite : {str(e)}"
            )
            await self.message.edit(embed=error_embed, view=self)

            # Log l'erreur
            import logging
            logger = logging.getLogger('moddy')
            logger.error(f"Erreur déploiement : {e}", exc_info=True)

        self.stop()

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Annule le déploiement"""
        # Désactive tous les boutons
        for item in self.children:
            item.disabled = True

        cancel_embed = discord.Embed(
            title="Déploiement annulé",
            description="Le déploiement a été annulé. Aucune modification n'a été appliquée.",
            color=COLORS["info"]
        )

        await interaction.response.edit_message(embed=cancel_embed, view=self)
        self.stop()

    async def on_timeout(self):
        """Appelé après le timeout"""
        if not self.confirmed and self.message:
            # Désactive tous les boutons
            for item in self.children:
                item.disabled = True

            try:
                timeout_embed = discord.Embed(
                    title="Temps écoulé",
                    description="La demande de déploiement a expiré.",
                    color=COLORS["info"]
                )

                await self.message.edit(embed=timeout_embed, view=self)
            except:
                pass


async def setup(bot):
    await bot.add_cog(Deploy(bot))