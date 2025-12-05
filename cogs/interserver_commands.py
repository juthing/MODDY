"""
Commandes /interserver - Gestion des messages inter-serveur
Permet de signaler et d'obtenir des informations sur les messages inter-serveur
"""

import discord
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional
import logging
from datetime import datetime, timezone

from utils.i18n import t
from config import EMOJIS
from utils.components_v2 import create_error_message, create_info_message, create_success_message
from cogs.error_handler import BaseView

logger = logging.getLogger('moddy.cogs.interserver_commands')

# IDs des salons de rapports et de logs
REPORT_CHANNEL_ID = 1446560294733086750  # Salon de rapports généraux
ENGLISH_LOG_CHANNEL_ID = 1446555149031047388  # Logs anglais
FRENCH_LOG_CHANNEL_ID = 1446555476044284045  # Logs français


class InterServerCommands(commands.GroupCog, name="interserver"):
    """Commandes pour gérer les messages inter-serveur"""

    def __init__(self, bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(
        name="report",
        description="Report an inter-server message to the moderation team"
    )
    @app_commands.describe(
        moddy_id="The Moddy ID of the message to report (format: XXXX-XXXX)"
    )
    async def report(
        self,
        interaction: discord.Interaction,
        moddy_id: str
    ):
        """Signale un message inter-serveur à l'équipe de modération"""
        # Normalise le moddy_id
        moddy_id = moddy_id.strip().upper()

        # Récupère les informations du message
        msg_data = await self.bot.db.get_interserver_message(moddy_id)

        if not msg_data:
            view = create_error_message(
                "Message Not Found",
                f"No inter-server message found with ID `{moddy_id}`."
            )
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        # Vérifie si le message est déjà supprimé
        if msg_data['status'] == 'deleted':
            view = create_error_message(
                "Message Already Deleted",
                f"The message `{moddy_id}` has already been deleted."
            )
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        # Crée le rapport dans le salon de rapports
        try:
            report_channel = self.bot.get_channel(REPORT_CHANNEL_ID)
            if not report_channel:
                view = create_error_message(
                    "Error",
                    "Could not access the report channel. Please contact the Moddy team."
                )
                await interaction.response.send_message(view=view, ephemeral=True)
                return

            # Récupère l'auteur du message
            try:
                author = await self.bot.fetch_user(msg_data['author_id'])
                author_mention = f"{author.mention} (`{author.id}`)"
            except:
                author_mention = f"Unknown User (`{msg_data['author_id']}`)"

            # Crée le rapport avec Components V2
            class ReportView(discord.ui.LayoutView):
                def __init__(self, bot, moddy_id: str, reporter_id: int):
                    super().__init__()
                    self.bot = bot
                    self.moddy_id = moddy_id
                    self.reporter_id = reporter_id
                    self.claimed_by = None

                container1 = discord.ui.Container(
                    discord.ui.TextDisplay(content=f"### <:warning:1398729560895422505> Inter-Server Report"),
                    discord.ui.TextDisplay(content=f"**Moddy ID:** `{moddy_id}`\n**Author:** {author_mention}\n**Server:** {interaction.guild.name} (`{interaction.guild.id}`)\n**Reported by:** {interaction.user.mention} (`{interaction.user.id}`)\n**Content:**\n{msg_data['content'][:1000] if msg_data['content'] else '*No content*'}"),
                )

                @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary, emoji="👋")
                async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    """Permet à un modérateur de claim le rapport"""
                    # Vérifie les permissions
                    from utils.staff_permissions import staff_permissions, StaffRole
                    user_roles = await staff_permissions.get_user_roles(interaction.user.id)

                    # Vérifie si l'utilisateur est au moins modérateur
                    allowed_roles = [StaffRole.Dev, StaffRole.Manager, StaffRole.Supervisor_Mod, StaffRole.Moderator]
                    if not any(role in allowed_roles for role in user_roles):
                        await interaction.response.send_message(
                            "You don't have permission to claim reports.",
                            ephemeral=True
                        )
                        return

                    self.claimed_by = interaction.user

                    # Met à jour le message
                    self.container1 = discord.ui.Container(
                        discord.ui.TextDisplay(content=f"### <:warning:1398729560895422505> Inter-Server Report"),
                        discord.ui.TextDisplay(content=f"**Moddy ID:** `{self.moddy_id}`\n**Author:** {author_mention}\n**Server:** {interaction.guild.name} (`{interaction.guild.id}`)\n**Reported by:** <@{self.reporter_id}> (`{self.reporter_id}`)\n**Claimed by:** {interaction.user.mention}\n**Content:**\n{msg_data['content'][:1000] if msg_data['content'] else '*No content*'}"),
                    )

                    # Désactive le bouton claim et active le bouton processed
                    button.disabled = True
                    self.skip_button.disabled = True

                    await interaction.response.edit_message(view=self)

                @discord.ui.button(label="Processed", style=discord.ButtonStyle.success, emoji="✅", disabled=True)
                async def processed_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    """Marque le rapport comme traité avec un formulaire pour les actions prises"""
                    # Vérifie si le rapport a été claim
                    if not self.claimed_by:
                        await interaction.response.send_message(
                            "Please claim the report first before marking it as processed.",
                            ephemeral=True
                        )
                        return

                    # Ouvre un modal pour les actions prises
                    modal = ProcessedModal(self.moddy_id)
                    await interaction.response.send_modal(modal)

                @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
                async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    """Skip le rapport sans raison"""
                    # Vérifie les permissions
                    from utils.staff_permissions import staff_permissions, StaffRole
                    user_roles = await staff_permissions.get_user_roles(interaction.user.id)

                    allowed_roles = [StaffRole.Dev, StaffRole.Manager, StaffRole.Supervisor_Mod, StaffRole.Moderator]
                    if not any(role in allowed_roles for role in user_roles):
                        await interaction.response.send_message(
                            "You don't have permission to skip reports.",
                            ephemeral=True
                        )
                        return

                    # Met à jour le message
                    self.container1 = discord.ui.Container(
                        discord.ui.TextDisplay(content=f"### <:warning:1398729560895422505> Inter-Server Report - Skipped"),
                        discord.ui.TextDisplay(content=f"**Moddy ID:** `{self.moddy_id}`\n**Skipped by:** {interaction.user.mention}\n**Reason:** No action required"),
                    )

                    # Désactive tous les boutons
                    for item in self.children:
                        if isinstance(item, discord.ui.Button):
                            item.disabled = True

                    await interaction.response.edit_message(view=self)

            # Envoie le rapport
            report_view = ReportView(self.bot, moddy_id, interaction.user.id)
            await report_channel.send(view=report_view)

            # Confirme à l'utilisateur
            view = create_success_message(
                "Report Sent",
                f"Your report for message `{moddy_id}` has been sent to the moderation team.\n\nThank you for helping keep the inter-server chat safe!"
            )
            await interaction.response.send_message(view=view, ephemeral=True)

            logger.info(f"Report sent for message {moddy_id} by {interaction.user} ({interaction.user.id})")

        except Exception as e:
            logger.error(f"Error sending report: {e}", exc_info=True)
            view = create_error_message(
                "Error",
                f"An error occurred while sending your report. Please try again later."
            )
            await interaction.response.send_message(view=view, ephemeral=True)

    @app_commands.command(
        name="info",
        description="Get information about an inter-server message"
    )
    @app_commands.describe(
        moddy_id="The Moddy ID of the message to get info about",
        incognito="Hide your identity in the request (default: False)"
    )
    async def info(
        self,
        interaction: discord.Interaction,
        moddy_id: str,
        incognito: bool = False
    ):
        """Obtient des informations sur un message inter-serveur"""
        # Normalise le moddy_id
        moddy_id = moddy_id.strip().upper()

        # Récupère les informations du message
        msg_data = await self.bot.db.get_interserver_message(moddy_id)

        if not msg_data:
            view = create_error_message(
                "Message Not Found",
                f"No inter-server message found with ID `{moddy_id}`."
            )
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        # Récupère l'auteur du message
        try:
            author = await self.bot.fetch_user(msg_data['author_id'])
            author_info = f"{author.mention} (`{author.id}`)"
        except:
            author_info = f"Unknown User (`{msg_data['author_id']}`)"

        # Récupère le serveur d'origine
        original_guild = self.bot.get_guild(msg_data['original_guild_id'])
        guild_info = f"{original_guild.name} (`{original_guild.id}`)" if original_guild else f"Unknown Server (`{msg_data['original_guild_id']}`)"

        # Compte les serveurs relayés
        relayed_count = len(msg_data.get('relayed_messages', []))

        # Format timestamp
        timestamp = msg_data.get('timestamp', msg_data.get('created_at'))
        timestamp_str = f"<t:{int(timestamp.timestamp())}:R>" if timestamp else "Unknown"

        # Crée l'interface avec Components V2
        class InfoView(discord.ui.LayoutView):
            container1 = discord.ui.Container(
                discord.ui.TextDisplay(content=f"### <:info:1401614681440784477> Inter-Server Message Info"),
                discord.ui.TextDisplay(content=f"**Moddy ID:** `{moddy_id}`\n**Author:** {author_info}\n**Original Server:** {guild_info}\n**Sent:** {timestamp_str}\n**Relayed to:** {relayed_count} servers\n**Status:** {msg_data['status']}\n**Moddy Team Message:** {'✅ Yes' if msg_data.get('is_moddy_team') else '❌ No'}\n\n**Content:**\n{msg_data['content'][:500] if msg_data['content'] else '*No content*'}"),
            )

        view = InfoView()

        # Log l'info request si pas incognito
        if not incognito:
            logger.info(f"Info request for message {moddy_id} by {interaction.user} ({interaction.user.id})")

        await interaction.response.send_message(view=view, ephemeral=True)


class ProcessedModal(discord.ui.Modal, title="Report Processing"):
    """Modal pour les actions prises sur un rapport"""

    actions_taken = discord.ui.TextInput(
        label="Actions Taken",
        placeholder="Describe the actions you took...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    def __init__(self, moddy_id: str):
        super().__init__()
        self.moddy_id = moddy_id

    async def on_submit(self, interaction: discord.Interaction):
        """Appelé quand le formulaire est soumis"""
        # Met à jour le message
        await interaction.response.edit_message(
            content=f"### <:done:1398729525277229066> Report Processed\n\n**Moddy ID:** `{self.moddy_id}`\n**Processed by:** {interaction.user.mention}\n**Actions taken:**\n{self.actions_taken.value}"
        )

        logger.info(f"Report {self.moddy_id} processed by {interaction.user} ({interaction.user.id})")


async def setup(bot):
    await bot.add_cog(InterServerCommands(bot))
