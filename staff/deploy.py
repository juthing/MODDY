"""
Commande deploy pour développeurs
Permet de mettre à jour le bot depuis GitHub directement sur le VPS
"""

import discord
from discord.ext import commands
import subprocess
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import os

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

        # Git fetch pour voir s'il y a des changements
        try:
            # Configure Git pour ne pas demander de credentials interactivement
            env = os.environ.copy()
            env['GIT_TERMINAL_PROMPT'] = '0'

            # Git fetch pour voir s'il y a des changements
            fetch_result = subprocess.run(
                ["git", "fetch"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
                env=env
            )

            if fetch_result.returncode != 0:
                error_embed = ModdyResponse.error(
                    "Erreur Git Fetch",
                    f"```\n{fetch_result.stderr}\n```"
                )
                await checking_msg.edit(embed=error_embed)
                return

            # Vérifie s'il y a des changements
            status_result = subprocess.run(
                ["git", "status", "-uno"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )

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

            confirm_embed.add_field(
                name="<:info:1401614681440784477> Instructions",
                value=(
                    "1. Confirme le déploiement\n"
                    "2. Entre tes credentials GitHub\n"
                    "3. Attends la fin du pull\n"
                    "4. Redémarre le VPS depuis Hostinger"
                ),
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
        # Ouvre le modal pour les credentials
        modal = GitHubCredentialsModal(self.bot, self.branch, self.commits_count, self.message, self.author)
        await interaction.response.send_modal(modal)

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


class GitHubCredentialsModal(discord.ui.Modal, title="Authentification GitHub"):
    """Modal pour entrer les credentials GitHub de manière sécurisée"""

    def __init__(self, bot, branch, commits_count, message, author):
        super().__init__()
        self.bot = bot
        self.branch = branch
        self.commits_count = commits_count
        self.message = message
        self.author = author

    username = discord.ui.TextInput(
        label="Nom d'utilisateur GitHub",
        placeholder="ton-username",
        max_length=100,
        required=True
    )

    token = discord.ui.TextInput(
        label="Token d'accès personnel GitHub",
        placeholder="ghp_xxxxxxxxxxxxxxxxxxxx",
        max_length=200,
        required=True,
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Quand le formulaire est soumis"""
        # Désactive les boutons du message original
        if self.message and hasattr(self.message, 'components') and self.message.components:
            view = discord.ui.View()
            for item in self.message.components[0].children:
                item.disabled = True
                view.add_item(item)
            await self.message.edit(view=view)

        # Embed de déploiement en cours
        deploy_embed = discord.Embed(
            title="<:loading:1395047662092550194> Déploiement en cours...",
            description="Récupération des modifications depuis GitHub",
            color=COLORS["info"],
            timestamp=datetime.utcnow()
        )
        deploy_embed.set_footer(text="Cette opération peut prendre quelques secondes")

        await interaction.response.send_message(embed=deploy_embed, ephemeral=True)

        try:
            # Créer les variables d'environnement avec les credentials
            env = os.environ.copy()
            env['GIT_TERMINAL_PROMPT'] = '0'  # Désactive les prompts
            env['GIT_ASKPASS'] = 'echo'  # Empêche Git de demander

            # Récupère l'URL actuelle du remote
            remote_result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )

            if remote_result.returncode != 0:
                raise Exception("Impossible de récupérer l'URL du remote")

            current_url = remote_result.stdout.strip()

            # Sauvegarde l'URL originale pour la restaurer après
            original_url = current_url

            # Parse l'URL pour injecter les credentials
            if current_url.startswith("https://"):
                # Enlève https://
                url_without_protocol = current_url.replace("https://", "")
                # Ajoute les credentials
                authenticated_url = f"https://{self.username.value}:{self.token.value}@{url_without_protocol}"
            elif current_url.startswith("git@"):
                # Convertit SSH en HTTPS
                # git@github.com:user/repo.git -> https://github.com/user/repo.git
                url_parts = current_url.replace("git@", "").replace(":", "/", 1)
                authenticated_url = f"https://{self.username.value}:{self.token.value}@{url_parts}"
            else:
                raise Exception("Format d'URL non supporté")

            # Configure temporairement le remote avec les credentials
            subprocess.run(
                ["git", "remote", "set-url", "origin", authenticated_url],
                cwd=Path(__file__).parent.parent,
                check=True
            )

            # Git pull avec les variables d'environnement
            pull_result = subprocess.run(
                ["git", "pull", "origin", self.branch],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
                env=env
            )

            # IMPORTANT: Restaure l'URL sans credentials pour la sécurité
            subprocess.run(
                ["git", "remote", "set-url", "origin", original_url],
                cwd=Path(__file__).parent.parent,
                check=True
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

                await interaction.edit_original_response(embed=success_embed)

                # Met à jour le message original aussi
                if self.message:
                    await self.message.edit(embed=success_embed, view=None)

                # Log l'action
                if log_cog := self.bot.get_cog("LoggingSystem"):
                    await log_cog.log_command(
                        type('obj', (object,), {
                            'author': self.author,
                            'guild': None,
                            'channel': self.message.channel if self.message else None
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

                # Nettoie l'output pour ne pas exposer les credentials
                error_output = error_output.replace(self.username.value, "[USERNAME]")
                error_output = error_output.replace(self.token.value, "[TOKEN]")

                if len(error_output) > 1000:
                    error_output = error_output[:997] + "..."

                error_embed.add_field(
                    name="Détails de l'erreur",
                    value=f"```\n{error_output}\n```",
                    inline=False
                )

                # Vérifie si c'est une erreur d'authentification
                if "Authentication failed" in error_output or "Invalid username or password" in error_output:
                    error_embed.add_field(
                        name="<:info:1401614681440784477> Problème d'authentification",
                        value=(
                            "• Vérifie ton nom d'utilisateur\n"
                            "• Utilise un **Personal Access Token**, pas ton mot de passe\n"
                            "• Le token doit avoir les permissions `repo`\n"
                            "• [Créer un token](https://github.com/settings/tokens/new)"
                        ),
                        inline=False
                    )
                else:
                    error_embed.add_field(
                        name="<:bug:1401614189482475551> Solutions possibles",
                        value=(
                            "• Vérifie qu'il n'y a pas de conflits\n"
                            "• Assure-toi que le token a les bonnes permissions\n"
                            "• Connecte-toi au VPS pour résoudre manuellement"
                        ),
                        inline=False
                    )

                await interaction.edit_original_response(embed=error_embed)

        except Exception as e:
            # IMPORTANT: Restaure l'URL en cas d'erreur
            try:
                if 'original_url' in locals():
                    subprocess.run(
                        ["git", "remote", "set-url", "origin", original_url],
                        cwd=Path(__file__).parent.parent
                    )
            except:
                pass

            # Erreur Python
            error_message = str(e).replace(self.username.value, "[USERNAME]").replace(self.token.value, "[TOKEN]")

            error_embed = ModdyResponse.error(
                "Erreur système",
                f"Une erreur s'est produite : {error_message}"
            )
            await interaction.edit_original_response(embed=error_embed)

            # Log l'erreur (sans les credentials)
            import logging
            logger = logging.getLogger('moddy')
            logger.error(f"Erreur déploiement : {error_message}")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        """Gestion des erreurs du modal"""
        await interaction.response.send_message(
            "<:undone:1398729502028333218> Une erreur s'est produite. Vérifie tes credentials.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Deploy(bot))