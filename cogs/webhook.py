"""
Webhook management command for Moddy
Allows users to inspect and manage Discord webhooks
"""

import discord
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional
import aiohttp
import re

from utils.embeds import ModdyEmbed, ModdyResponse, ModdyColors
from utils.incognito import add_incognito_option, get_incognito_setting
from utils.i18n import i18n


class WebhookView(ui.LayoutView):
    """View to manage webhook with Components V2"""

    def __init__(self, webhook_data: dict, author: discord.User, locale: str):
        super().__init__(timeout=300)
        self.webhook_data = webhook_data
        self.author = author
        self.locale = locale
        self.build_view()

    def build_view(self):
        """Builds the Components V2 view"""
        self.clear_items()

        # Create main container
        container = ui.Container()

        # Webhook info display
        webhook_info = self.format_webhook_info()
        container.add_item(ui.TextDisplay(webhook_info))

        # Add separator
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # Add instruction text
        instruction = "-# Use the buttons below to manage this webhook"
        container.add_item(ui.TextDisplay(instruction))

        # Add container to view
        self.add_item(container)

        # Create buttons manually
        delete_btn = ui.Button(label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="delete_webhook")
        delete_btn.callback = self.delete_webhook

        edit_btn = ui.Button(label="Edit", style=discord.ButtonStyle.primary, emoji="✏️", custom_id="edit_webhook")
        edit_btn.callback = self.show_edit_modal

        send_btn = ui.Button(label="Send Message", style=discord.ButtonStyle.success, emoji="📤", custom_id="send_webhook")
        send_btn.callback = self.show_send_modal

        refresh_btn = ui.Button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="refresh_webhook")
        refresh_btn.callback = self.refresh_webhook

        # Add buttons directly to the view
        self.add_item(delete_btn)
        self.add_item(edit_btn)
        self.add_item(send_btn)
        self.add_item(refresh_btn)

    def format_webhook_info(self) -> str:
        """Formats webhook information for display"""
        data = self.webhook_data

        # Get webhook type
        webhook_types = {
            1: "Incoming Webhook",
            2: "Channel Follower",
            3: "Application"
        }
        webhook_type = webhook_types.get(data.get('type', 1), "Unknown")

        # Avatar URL
        avatar_url = None
        if data.get('avatar'):
            avatar_url = f"https://cdn.discordapp.com/avatars/{data['id']}/{data['avatar']}.png?size=128"

        # Format info
        info = f"## 🔗 Webhook Information\n\n"
        info += f"**Name:** `{data.get('name', 'Unknown')}`\n"
        info += f"**ID:** `{data.get('id', 'N/A')}`\n"
        info += f"**Type:** `{webhook_type}`\n"
        info += f"**Channel:** <#{data.get('channel_id', '0')}>\n"
        info += f"**Server ID:** `{data.get('guild_id', 'N/A')}`\n"

        if avatar_url:
            info += f"**Avatar:** [View]({avatar_url})\n"

        return info

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Checks that it's the author using the buttons"""
        if interaction.user != self.author:
            await interaction.response.send_message(
                "You can't use these buttons, they belong to another user.",
                ephemeral=True
            )
            return False
        return True

    async def delete_webhook(self, interaction: discord.Interaction):
        """Deletes the webhook"""
        webhook_url = self.webhook_data.get('url')

        if not webhook_url:
            await interaction.response.send_message(
                embed=ModdyResponse.error("Error", "Webhook URL not found."),
                ephemeral=True
            )
            return

        # Confirm deletion
        await interaction.response.defer(ephemeral=True)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(webhook_url) as response:
                    if response.status == 204:
                        # Success
                        success_embed = ModdyResponse.success(
                            "Webhook Deleted",
                            f"The webhook **{self.webhook_data.get('name')}** has been successfully deleted."
                        )

                        # Disable all buttons
                        for item in self.children:
                            if isinstance(item, ui.Button):
                                item.disabled = True

                        await interaction.edit_original_response(view=self)
                        await interaction.followup.send(embed=success_embed, ephemeral=True)
                    else:
                        error_text = await response.text()
                        error_embed = ModdyResponse.error(
                            "Deletion Failed",
                            f"Could not delete the webhook. Status: {response.status}\n```{error_text[:100]}```"
                        )
                        await interaction.followup.send(embed=error_embed, ephemeral=True)
        except Exception as e:
            error_embed = ModdyResponse.error(
                "Error",
                f"An error occurred while deleting the webhook:\n```{str(e)[:100]}```"
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

    async def show_edit_modal(self, interaction: discord.Interaction):
        """Shows modal to edit webhook"""
        modal = EditWebhookModal(self.webhook_data, self)
        await interaction.response.send_modal(modal)

    async def show_send_modal(self, interaction: discord.Interaction):
        """Shows modal to send a message via webhook"""
        modal = SendMessageModal(self.webhook_data)
        await interaction.response.send_modal(modal)

    async def refresh_webhook(self, interaction: discord.Interaction):
        """Refreshes webhook information"""
        await interaction.response.defer()

        webhook_url = self.webhook_data.get('url')

        if not webhook_url:
            await interaction.followup.send(
                embed=ModdyResponse.error("Error", "Webhook URL not found."),
                ephemeral=True
            )
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(webhook_url) as response:
                    if response.status == 200:
                        self.webhook_data = await response.json()
                        self.build_view()
                        await interaction.edit_original_response(view=self)
                        await interaction.followup.send(
                            embed=ModdyResponse.success("Refreshed", "Webhook information has been updated."),
                            ephemeral=True
                        )
                    else:
                        error_embed = ModdyResponse.error(
                            "Refresh Failed",
                            f"Could not refresh webhook. Status: {response.status}"
                        )
                        await interaction.followup.send(embed=error_embed, ephemeral=True)
        except Exception as e:
            error_embed = ModdyResponse.error(
                "Error",
                f"An error occurred:\n```{str(e)[:100]}```"
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)


class EditWebhookModal(ui.Modal, title="Edit Webhook"):
    """Modal to edit webhook name and avatar"""

    def __init__(self, webhook_data: dict, view: WebhookView):
        super().__init__()
        self.webhook_data = webhook_data
        self.view = view

        # Add name input
        self.name_input = ui.TextInput(
            label="Webhook Name",
            placeholder="Enter new webhook name",
            default=webhook_data.get('name', ''),
            max_length=80,
            required=True
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        await interaction.response.defer(ephemeral=True)

        webhook_url = self.webhook_data.get('url')
        new_name = self.name_input.value

        if not webhook_url:
            await interaction.followup.send(
                embed=ModdyResponse.error("Error", "Webhook URL not found."),
                ephemeral=True
            )
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.patch(webhook_url, json={"name": new_name}) as response:
                    if response.status == 200:
                        updated_data = await response.json()
                        self.view.webhook_data = updated_data
                        self.view.build_view()

                        await interaction.edit_original_response(view=self.view)

                        success_embed = ModdyResponse.success(
                            "Webhook Updated",
                            f"The webhook has been renamed to **{new_name}**."
                        )
                        await interaction.followup.send(embed=success_embed, ephemeral=True)
                    else:
                        error_text = await response.text()
                        error_embed = ModdyResponse.error(
                            "Update Failed",
                            f"Could not update the webhook. Status: {response.status}\n```{error_text[:100]}```"
                        )
                        await interaction.followup.send(embed=error_embed, ephemeral=True)
        except Exception as e:
            error_embed = ModdyResponse.error(
                "Error",
                f"An error occurred:\n```{str(e)[:100]}```"
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)


class SendMessageModal(ui.Modal, title="Send Message via Webhook"):
    """Modal to send a message through the webhook"""

    def __init__(self, webhook_data: dict):
        super().__init__()
        self.webhook_data = webhook_data

        # Message content input
        self.message_input = ui.TextInput(
            label="Message Content",
            placeholder="Enter the message to send",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        self.add_item(self.message_input)

        # Username override (optional)
        self.username_input = ui.TextInput(
            label="Username Override (Optional)",
            placeholder="Leave empty to use webhook's default name",
            max_length=80,
            required=False
        )
        self.add_item(self.username_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        await interaction.response.defer(ephemeral=True)

        webhook_url = self.webhook_data.get('url')
        message_content = self.message_input.value
        username = self.username_input.value or None

        if not webhook_url:
            await interaction.followup.send(
                embed=ModdyResponse.error("Error", "Webhook URL not found."),
                ephemeral=True
            )
            return

        # Build payload
        payload = {"content": message_content}
        if username:
            payload["username"] = username

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status in [200, 204]:
                        success_embed = ModdyResponse.success(
                            "Message Sent",
                            f"Your message has been sent successfully via the webhook!"
                        )
                        await interaction.followup.send(embed=success_embed, ephemeral=True)
                    else:
                        error_text = await response.text()
                        error_embed = ModdyResponse.error(
                            "Send Failed",
                            f"Could not send the message. Status: {response.status}\n```{error_text[:100]}```"
                        )
                        await interaction.followup.send(embed=error_embed, ephemeral=True)
        except Exception as e:
            error_embed = ModdyResponse.error(
                "Error",
                f"An error occurred:\n```{str(e)[:100]}```"
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)


class Webhook(commands.Cog):
    """Webhook management system"""

    def __init__(self, bot):
        self.bot = bot

    def extract_webhook_info(self, webhook_input: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extracts webhook ID and token from a URL or token string

        Returns:
            tuple: (webhook_id, webhook_token) or (None, None) if invalid
        """
        # Pattern for full webhook URL
        url_pattern = r'https?://discord\.com/api/webhooks/(\d+)/([a-zA-Z0-9_-]+)'

        # Try to match full URL
        match = re.match(url_pattern, webhook_input)
        if match:
            return match.group(1), match.group(2)

        # Pattern for ID/Token format
        id_token_pattern = r'^(\d+)/([a-zA-Z0-9_-]+)$'
        match = re.match(id_token_pattern, webhook_input)
        if match:
            return match.group(1), match.group(2)

        return None, None

    async def fetch_webhook_data(self, webhook_id: str, webhook_token: str) -> Optional[dict]:
        """Fetches webhook data from Discord API"""
        webhook_url = f"https://discord.com/api/webhooks/{webhook_id}/{webhook_token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(webhook_url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
        except Exception:
            return None

    @app_commands.command(
        name="webhook",
        description="Inspect and manage Discord webhooks"
    )
    @app_commands.describe(
        webhook="Webhook URL or ID/Token",
        incognito="Make response visible only to you"
    )
    @add_incognito_option()
    async def webhook_command(
        self,
        interaction: discord.Interaction,
        webhook: str,
        incognito: Optional[bool] = None
    ):
        """Main webhook management command"""

        # Get the user's locale from Discord
        locale = i18n.get_user_locale(interaction)

        # Get the ephemeral mode
        ephemeral = get_incognito_setting(interaction)

        # Show loading message
        await interaction.response.send_message(
            content="<a:loading:1395047662092550194> **Fetching webhook information...**",
            ephemeral=ephemeral
        )

        # Extract webhook info
        webhook_id, webhook_token = self.extract_webhook_info(webhook)

        if not webhook_id or not webhook_token:
            error_embed = ModdyResponse.error(
                "Invalid Webhook",
                "Please provide a valid webhook URL or ID/Token.\n\n"
                "**Valid formats:**\n"
                "• `https://discord.com/api/webhooks/ID/TOKEN`\n"
                "• `ID/TOKEN`"
            )
            await interaction.edit_original_response(content=None, embed=error_embed)
            return

        # Fetch webhook data
        webhook_data = await self.fetch_webhook_data(webhook_id, webhook_token)

        if not webhook_data:
            error_embed = ModdyResponse.error(
                "Webhook Not Found",
                "Could not fetch webhook information. The webhook may be invalid or deleted."
            )
            await interaction.edit_original_response(content=None, embed=error_embed)
            return

        # Create the view with webhook management
        view = WebhookView(webhook_data, interaction.user, locale)

        await interaction.edit_original_response(content=None, embed=None, view=view)


async def setup(bot):
    await bot.add_cog(Webhook(bot))
